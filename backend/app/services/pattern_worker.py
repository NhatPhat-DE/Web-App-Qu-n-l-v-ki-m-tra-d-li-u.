"""Disposable spawn worker. Imports no application configuration or database code.
IPC uses parent-owned temporary files, not a pipe whose large writes require draining.
Only column values, expressions and row/rule ordinals cross the boundary.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import multiprocessing
import pickle
from pathlib import Path
import struct
import tempfile
import threading
import time

MAX_RULES = 10
MAX_VALUE_POINTS = 4096
MAX_VALUE_BYTES = 16384
MAX_MATCH_BYTES = 50 * 1024 * 1024
MAX_MEM = 8 * 1024 * 1024
DEADLINE_SECONDS = 5.0
_GATE = threading.Lock()
CANCEL_EVENT = ContextVar('pattern_cancel_event', default=None)
_RECORD = struct.Struct('<II')


class PatternError(Exception):
    def __init__(self, code, message, status=503):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


def preflight(header, rows, rules):
    patterns = [rule for rule in rules if rule['rule_type'] == 'pattern']
    if len(patterns) > MAX_RULES:
        raise PatternError('PATTERN_RULE_LIMIT', 'Tối đa 10 quy tắc pattern đang bật trong một lần chạy.', 422)
    total = 0
    for rule in patterns:
        index = header.index(rule['columns'][0])
        for row in rows:
            value = row[index]
            if value is None or isinstance(value, str) and not value.strip():
                continue
            if not isinstance(value, str):
                raise PatternError('PATTERN_VALUE_INVALID', 'Pattern chỉ kiểm tra giá trị chuỗi nguyên bản.', 422)
            try:
                size = len(value.encode('utf-8'))
            except UnicodeError:
                raise PatternError('PATTERN_VALUE_INVALID', 'Giá trị pattern không biểu diễn được bằng UTF-8.', 422) from None
            if len(value) > MAX_VALUE_POINTS or size > MAX_VALUE_BYTES:
                raise PatternError('PATTERN_VALUE_LIMIT', 'Giá trị kiểm tra vượt 4096 code point hoặc 16 KiB UTF-8; không cắt dữ liệu.', 422)
            total += size
            if total > MAX_MATCH_BYTES:
                raise PatternError('PATTERN_BYTE_BUDGET', 'Tổng dữ liệu match lặp theo quy tắc vượt 50 MiB UTF-8.', 422)
    return patterns


@contextmanager
def admission(enabled):
    acquired = False
    if enabled:
        acquired = _GATE.acquire(blocking=False)
        if not acquired:
            raise PatternError('PATTERN_WORKER_BUSY', 'Một worker pattern đang bận; hãy thử lại bằng thao tác người dùng.', 409)
    try:
        yield
    finally:
        if acquired:
            _GATE.release()


def worker_main(folder):
    # A single run owns these files. Child never writes a DB, token or parent lock.
    import re2
    folder = Path(folder)
    options = re2.Options()
    options.max_mem = MAX_MEM
    options.log_errors = False
    options.case_sensitive = True
    options.dot_nl = False
    try:
        with (folder / 'input').open('rb') as source, (folder / 'output').open('wb') as target:
            count = pickle.load(source)
            for ordinal in range(count):
                pattern, size = pickle.load(source)
                expression = re2.compile(pattern, options=options)
                for _ in range(size):
                    number, value = pickle.load(source)
                    if expression.fullmatch(value) is None:
                        target.write(_RECORD.pack(ordinal, number))
        (folder / 'done').write_text('ok', encoding='ascii')
    except MemoryError:
        (folder / 'done').write_text('resource', encoding='ascii')
    except re2.error:
        (folder / 'done').write_text('compile', encoding='ascii')
    # Other failures leave no completion marker and become WORKER_FAILED.


def evaluate(header, rows, patterns, *, worker_target=None):
    """Called with admission held, from the synchronous run endpoint thread.
    Deadline includes input serialization, spawn, compile, match and output read.
    Child output is fixed-width binary (8 bytes/mismatch), never a blocking Pipe.
    """
    if not patterns:
        return {}
    deadline = time.monotonic() + DEADLINE_SECONDS
    def check_time():
        cancelled = CANCEL_EVENT.get()
        if cancelled is not None and cancelled.is_set():
            raise PatternError('PATTERN_CANCELLED', 'Phase pattern đã bị hủy; không lưu kết quả một phần.')
        if time.monotonic() >= deadline:
            raise PatternError('PATTERN_TIMEOUT', 'Phase pattern vượt deadline 5 giây; không lưu kết quả một phần.')
    process = None
    try:
        with tempfile.TemporaryDirectory(prefix='datalens-pattern-') as folder:
            try:
                with (Path(folder) / 'input').open('wb') as target:
                    pickle.dump(len(patterns), target, protocol=5)
                    for rule in patterns:
                        index = header.index(rule['columns'][0])
                        count = sum(1 for row in rows if row[index] is not None and row[index].strip())
                        pickle.dump((rule['config']['pattern'], count), target, protocol=5)
                        for number, row in enumerate(rows, 1):
                            check_time()
                            value = row[index]
                            if value is not None and value.strip():
                                pickle.dump((number, value), target, protocol=5)
                check_time()
                process = multiprocessing.get_context('spawn').Process(target=worker_target or worker_main, args=(folder,))
                process.start()
                while process.is_alive():
                    check_time()
                    process.join(timeout=min(0.02, max(0, deadline - time.monotonic())))
                check_time()
                marker = Path(folder) / 'done'
                state = marker.read_text(encoding='ascii') if marker.exists() else ''
                if process.exitcode != 0 or state != 'ok':
                    code = {'resource': 'PATTERN_RESOURCE_LIMIT', 'compile': 'PATTERN_COMPILE_FAILED'}.get(state, 'PATTERN_WORKER_FAILED')
                    raise PatternError(code, 'Worker pattern không hoàn tất an toàn; không lưu kết quả một phần.')
                result = {rule['rule_id']: set() for rule in patterns}
                with (Path(folder) / 'output').open('rb') as source:
                    while True:
                        check_time()
                        chunk = source.read(_RECORD.size * 4096)
                        if not chunk:
                            break
                        if len(chunk) % _RECORD.size:
                            raise PatternError('PATTERN_WORKER_FAILED', 'Kết quả worker pattern không hợp lệ.')
                        for ordinal, number in _RECORD.iter_unpack(chunk):
                            if ordinal >= len(patterns) or not 1 <= number <= len(rows):
                                raise PatternError('PATTERN_WORKER_FAILED', 'Kết quả worker pattern không hợp lệ.')
                            result[patterns[ordinal]['rule_id']].add(number)
                check_time()
                return result
            finally:
                if process is not None and process.pid is not None:
                    if process.is_alive():
                        process.terminate()
                    process.join(timeout=1)
                    if process.is_alive():
                        process.kill()
                        process.join()
                    process.close()
    except PatternError:
        raise
    except (OSError, MemoryError, EOFError, ValueError):
        raise PatternError('PATTERN_RESOURCE_LIMIT', 'Không đủ tài nguyên để hoàn tất phase pattern an toàn.') from None
