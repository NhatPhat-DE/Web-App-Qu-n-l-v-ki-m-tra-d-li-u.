"""AI orchestration boundary. Gemini is selected only with explicit configuration."""
import asyncio
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from math import ceil
from threading import Lock
from typing import Protocol
from app.services.ai_preview import confirm_preview, current_user
from app.services.ai_suggestions import parse_suggestions


class AIError(ValueError):
    def __init__(self,status,code,retry_after=None):
        self.status,self.code,self.retry_after=status,code,retry_after
        super().__init__('AI suggestions unavailable.')


@dataclass(frozen=True)
class Limits:
    connect_timeout: float = 5
    total_timeout: float = 20
    max_output_bytes: int = 16384
    max_output_tokens: int = 2000
    max_suggestions: int = 5


class Adapter(Protocol):
    async def suggest(self,payload: dict,limits: Limits) -> str | bytes: ...


def get_adapter() -> Adapter:
    from app.services.gemini_adapter import GeminiAdapter,configuration
    return GeminiAdapter(configuration())


class Quota:
    def __init__(self,clock=time.monotonic,wall=time.time,capacity=10000):
        self.clock,self.wall,self.capacity=clock,wall,capacity
        self.lock=Lock(); self.users={}; self.active=set(); self.day=None; self.daily=0
    def reserve(self,user):
        with self.lock:
            now=self.clock(); wall=self.wall()
            day=datetime.fromtimestamp(wall,timezone.utc).date()
            if day!=self.day: self.day=day; self.daily=0
            for key in list(self.users):
                values=self.users[key]
                while values and values[0]<=now-600: values.popleft()
                if not values: del self.users[key]
            if user in self.active: raise AIError(429,'AI_IN_PROGRESS',1)
            values=self.users.get(user)
            if values and len(values)>=5: raise AIError(429,'AI_QUOTA_EXCEEDED',max(1,ceil(values[0]+600-now)))
            if self.daily>=20:
                midnight=datetime.combine(day,datetime.min.time(),timezone.utc).timestamp()+86400
                raise AIError(429,'AI_QUOTA_EXCEEDED',max(1,ceil(midnight-wall)))
            if (values is None and len(self.users)>=self.capacity) or len(self.active)>=self.capacity:
                raise AIError(429,'AI_QUOTA_CAPACITY',600)
            self.users.setdefault(user,deque()).append(now)
            self.active.add(user); self.daily+=1
    def release(self,user):
        with self.lock: self.active.discard(user)


quota=Quota()
limits=Limits()
clock=time.monotonic


async def await_adapter(task,timeout):
    started=clock()
    done,_=await asyncio.wait({task},timeout=timeout)
    if task not in done or clock()-started>=timeout: raise TimeoutError()
    return task.result()


async def generate(dataset_id,version_id,preview_token,user_id,session_token):
    from starlette.concurrency import run_in_threadpool
    # Each helper closes its own DB connection before returning. No DB transaction
    # survives into the adapter await.
    payload=await run_in_threadpool(confirm_preview,preview_token,user_id,session_token,dataset_id,version_id)
    adapter=get_adapter()
    selected=[column['name'] for column in payload['columns']]
    reserved_quota=quota
    reserved_quota.reserve(user_id)
    task=None
    try:
        task=asyncio.create_task(adapter.suggest(payload,limits))
        try: raw=await await_adapter(task,limits.total_timeout)
        except AIError: raise
        except TimeoutError: raise AIError(504,'AI_TIMEOUT') from None
        except Exception: raise AIError(503,'AI_UNAVAILABLE') from None
        suggestions=parse_suggestions(raw,selected)
        await run_in_threadpool(current_user,user_id,session_token)
        return suggestions
    finally:
        if task is not None and not task.done():
            task.cancel()
            def finished(completed):
                reserved_quota.release(user_id)
                if not completed.cancelled(): completed.exception()  # Consume; never log provider data.
            task.add_done_callback(finished)
        else:
            reserved_quota.release(user_id)
