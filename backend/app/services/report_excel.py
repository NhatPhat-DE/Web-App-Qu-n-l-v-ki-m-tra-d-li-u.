"""Read-only Excel rendering of the existing schema-1 report, never an engine."""
from datetime import datetime
from decimal import Decimal, localcontext
from io import BytesIO
import json

import xlsxwriter
from app.services import quality_history
from app.services.dataset_catalog import CatalogNotFound
from app.services.quality_execution import RunError
from sqlalchemy.exc import SQLAlchemyError

XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
EXCEL_ROWS = 1_048_576
CELL_UTF16_UNITS = 32_767
MAX_LINE_FEEDS = 253
MAX_OUTPUT_BYTES = 32 * 1024 * 1024
MAX_RENDERED_BYTES = 64 * 1024 * 1024
EXPORT_LIMITS = {'violations': 100_000, 'rules': 10_000, 'bytes': 32 * 1024 * 1024}
RULE_LABELS = {'required': 'Bắt buộc có giá trị', 'unique': 'Không trùng',
               'numeric_range': 'Khoảng số', 'data_type': 'Đúng kiểu dữ liệu',
               'date_format': 'Ngày đúng định dạng', 'allowed_values': 'Thuộc tập giá trị cho phép', 'pattern': 'Khớp mẫu toàn chuỗi'}
TYPE_LABELS = {'integer': 'Số nguyên', 'decimal': 'Số thập phân hữu hạn', 'boolean': 'Boolean true/false viết thường'}


def reject(code, message, status=422):
    raise RunError(status, code, message + ' Hãy dùng báo cáo JSON để nhận đầy đủ dữ liệu.')


def check_characters(value):
    """Reject invalid XML characters in original data, even inside JSON arrays."""
    if isinstance(value, str):
        for char in value:
            number = ord(char)
            if not (number in (9, 10, 13) or 0x20 <= number <= 0xD7FF or 0xE000 <= number <= 0xFFFD or 0x10000 <= number <= 0x10FFFF):
                reject('XLSX_INVALID_CHARACTER', 'Báo cáo chứa ký tự không thể biểu diễn an toàn trong Excel.')
    elif isinstance(value, dict):
        for key, item in value.items():
            check_characters(key); check_characters(item)
    elif isinstance(value, (list, tuple)):
        for item in value: check_characters(item)


def text(value):
    if isinstance(value, datetime):
        if value.utcoffset() is None:
            reject('XLSX_INVALID_TIME', 'Thời gian báo cáo thiếu múi giờ.')
        return value.isoformat()
    if value is None: return 'null'
    return str(value)


def structured(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def expected_condition(rule):
    kind, columns, config = rule['rule_type'], structured(rule['columns']), rule['config']
    if kind == 'required': return f'Cột {columns} phải có giá trị; null, rỗng hoặc chỉ whitespace là thiếu.'
    if kind == 'unique': return f'Tổ hợp cột {columns} không được trùng nguyên bản; bỏ qua tổ hợp có giá trị thiếu.'
    if kind == 'numeric_range': return f'Cột {columns} là số hữu hạn trong khoảng đóng [{config["min"]}, {config["max"]}]; bỏ qua thiếu.'
    if kind == 'data_type': return f'Cột {columns} đúng kiểu yêu cầu {TYPE_LABELS[config["type"]]}; kiểm tra nguyên bản, không trim; bỏ qua thiếu.'
    if kind == 'date_format': return f'Cột {columns} đúng định dạng {config["format"]} và ngày Gregorian tồn tại; không đoán/trim; bỏ qua thiếu.' + (f' Khoảng ngày [{config["min"]}, {config["max"]}].' if 'min' in config else '')
    if kind == 'pattern': return f'Cột {columns} full match mẫu {structured(config["pattern"])}; dialect {config["dialect"]}; phân biệt hoa/thường và khoảng trắng; bỏ qua thiếu.'
    if kind == 'allowed_values': return f'Cột {columns} thuộc tập {structured(config["values"])}; phân biệt hoa/thường và khoảng trắng, không chuẩn hóa Unicode; bỏ qua thiếu.'
    reject('XLSX_UNSUPPORTED_RULE', 'Snapshot có loại quy tắc chưa hỗ trợ xuất Excel.')


def check_cell(value):
    check_characters(value)
    if len(value.encode('utf-16-le')) // 2 > CELL_UTF16_UNITS or value.count('\n') > MAX_LINE_FEEDS:
        reject('XLSX_CELL_LIMIT', 'Nội dung ô vượt giới hạn Excel (32767 UTF-16 code unit hoặc 253 xuống dòng).')


def workbook_bytes(report):
    check_characters(report)
    if len(report['violations']) + 1 > EXCEL_ROWS or len(report['rule_snapshot']) + 1 > EXCEL_ROWS:
        reject('XLSX_ROW_LIMIT', 'Số dòng báo cáo vượt giới hạn worksheet Excel.', 413)
    if len(report['violations']) > EXPORT_LIMITS['violations'] or len(report['rule_snapshot']) > EXPORT_LIMITS['rules']:
        reject('XLSX_EXPORT_LIMIT', 'Báo cáo vượt giới hạn xuất Excel.', 413)
    # Defensive budget for callers other than the database reader.
    if len(json.dumps(report, ensure_ascii=False, default=str, separators=(',', ':')).encode('utf-8')) > EXPORT_LIMITS['bytes']:
        reject('XLSX_EXPORT_LIMIT', 'Báo cáo vượt giới hạn dung lượng xuất Excel.', 413)
    snapshot = {rule['id']: rule for rule in report['rule_snapshot']}
    conditions = {rule['id']: expected_condition(rule) for rule in report['rule_snapshot']}
    dataset, version, run = report['dataset'], report['version'], report['run']
    with localcontext() as context:
        context.prec = 24
        pass_rate = format(Decimal(100) - Decimal(run['error_row_rate']), '.4f')
    overview = [
        ('Báo cáo chất lượng dữ liệu', 'DataLens DQ'),
        ('Dataset ID', dataset['id']), ('Tên dataset', dataset['name']),
        ('Nguồn metadata', 'Metadata tại thời điểm xuất (current_at_export)'),
        ('Ghi chú metadata', report['dataset_metadata_note']),
        ('Mô tả tại thời điểm xuất', dataset['description']), ('Nguồn tại thời điểm xuất', dataset['source']),
        ('Người phụ trách tại thời điểm xuất', dataset['owner']),
        ('Version ID', version['id']), ('Phiên bản', version['version_number']), ('Tên file CSV', version['original_filename']),
        ('Thời điểm nhập', version['imported_at']), ('Run ID', run['id']), ('Trạng thái', run['status']),
        ('Bắt đầu', run['started_at']), ('Kết thúc', run['finished_at']), ('Engine version', run['engine_version']),
        ('Thời điểm xuất', report['exported_at']), ('Tổng bản ghi', run['total_rows']),
        ('Bản ghi lỗi', run['error_row_count']), ('Tổng vi phạm', run['violation_count']),
        ('Tỷ lệ lỗi', run['error_row_rate'] + '%'), ('Tỷ lệ đạt', pass_rate + '%'),
        ('Lưu ý thống kê', 'Một bản ghi có thể có nhiều vi phạm.'),
        ('Giới hạn kết luận', 'Đạt theo các quy tắc đã áp dụng không chứng minh dữ liệu đúng hoàn toàn.'),
        ('Kết quả', 'Không phát hiện vi phạm.' if not report['violations'] else 'Chi tiết đầy đủ ở sheet Chi tiết lỗi; điều kiện lấy từ snapshot.'),
    ]
    supplier=report.get('supplier')
    overview.extend([('Thương hiệu nguồn (snapshot)',f"{supplier['brand_code']} · {supplier['brand_name']}" if supplier else 'Chưa xác định cửa hàng'),
        ('Cửa hàng cung cấp (snapshot)',f"{supplier['store_code']} · {supplier['store_name']}" if supplier else 'Chưa xác định cửa hàng')])
    output = BytesIO()
    rendered_bytes = 0
    # constant_memory flushes rows to temporary XML files, not a complete cell graph.
    # Do not enable in_memory: that would override constant_memory.
    with xlsxwriter.Workbook(output, {'constant_memory': True, 'strings_to_formulas': False,
                                       'strings_to_numbers': False, 'strings_to_urls': False}) as book:
        body = book.add_format({'text_wrap': True, 'valign': 'top', 'num_format': '@'})
        header = book.add_format({'bold': True, 'bg_color': '#174F56', 'font_color': 'white', 'text_wrap': True, 'valign': 'top', 'num_format': '@'})
        def sheet(name, titles, widths):
            target = book.add_worksheet(name)
            target.freeze_panes(1, 0)
            for index, width in enumerate(widths): target.set_column(index, index, width, body)
            put(target, 0, titles, header)
            target.set_row(0, 32)
            return target
        def put(target, index, values, style=body):
            nonlocal rendered_bytes
            if index >= EXCEL_ROWS: reject('XLSX_ROW_LIMIT', 'Số dòng vượt giới hạn Excel.', 413)
            for column, value in enumerate(values):
                value = text(value); check_cell(value)
                rendered_bytes += len(value.encode('utf-8'))
                if rendered_bytes > MAX_RENDERED_BYTES:
                    reject('XLSX_EXPORT_LIMIT', 'Tổng nội dung ô Excel vượt giới hạn xuất.', 413)
                # Always explicit text, including =/+/-/@, URLs, IDs and long numbers.
                if target.write_string(index, column, value, style) != 0:
                    reject('XLSX_CELL_LIMIT', 'Không thể ghi đầy đủ nội dung ô Excel.')
        main = sheet('Tổng quan', ['Thông tin', 'Giá trị'], [36, 110])
        for index, pair in enumerate(overview, 1): put(main, index, pair)
        errors = sheet('Chi tiết lỗi', ['Số thứ tự bản ghi', 'Tên quy tắc (snapshot)', 'Loại quy tắc', 'Cột (JSON)',
                                     'Giá trị nguyên bản (JSON)', 'Điều kiện mong đợi (snapshot)', 'Mã lỗi', 'Giải thích đã lưu'], [20, 32, 38, 32, 52, 85, 36, 85])
        for index, violation in enumerate(report['violations'], 1):
            rule = snapshot[violation['rule_id_snapshot']]
            put(errors, index, [violation['row_number'], rule['name'], RULE_LABELS[rule['rule_type']] + ' (' + rule['rule_type'] + ')',
                structured(violation['columns']), structured(violation['values']), conditions[rule['id']], violation['error_code'], violation['message']])
        errors.autofilter(0, 0, max(1, len(report['violations'])), 7)
        if not report['violations']: put(errors, 1, ['Không phát hiện vi phạm.'])
        rules = sheet('Quy tắc đã áp dụng', ['Snapshot ID', 'Tên quy tắc', 'Loại quy tắc', 'Cột (JSON)', 'Điều kiện dễ đọc', 'Config nguyên bản (JSON)'], [20, 32, 38, 32, 85, 70])
        for index, rule in enumerate(report['rule_snapshot'], 1):
            put(rules, index, [rule['id'], rule['name'], RULE_LABELS[rule['rule_type']] + ' (' + rule['rule_type'] + ')',
                              structured(rule['columns']), conditions[rule['id']], structured(rule['config'])])
        rules.autofilter(0, 0, max(1, len(report['rule_snapshot'])), 5)
    if output.tell() > MAX_OUTPUT_BYTES: reject('XLSX_EXPORT_LIMIT', 'File Excel vượt giới hạn dung lượng xuất.', 413)
    return output.getvalue()


def export_xlsx(dataset_id, run_id):
    try:
        data = quality_history.export_report(dataset_id, run_id, limits=EXPORT_LIMITS)
        return workbook_bytes(data)
    except (RunError, CatalogNotFound, SQLAlchemyError, ConnectionError):
        raise
    except Exception:
        # Native/library/filesystem details must never reach the response.
        raise RunError(503, 'XLSX_EXPORT_FAILED', 'Không thể xuất Excel lúc này. Hãy thử báo cáo JSON; không có dữ liệu nào bị thay đổi.') from None
