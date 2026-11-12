from collections import deque
from threading import Lock
from time import monotonic
import math


class LoginLimited(Exception):
    def __init__(self, retry_after):
        self.retry_after = retry_after


class LoginLimiter:
    def __init__(self, clock=monotonic, capacity=10000):
        self.clock, self.capacity = clock, capacity
        self.lock = Lock()
        self.counters = {}

    def reserve(self, ip, username):
        with self.lock:
            now = self.clock()
            for key in list(self.counters):
                counter = self.counters[key]
                while counter and counter[0] <= now-600: counter.popleft()
                if not counter: del self.counters[key]
            keys = [('ip', ip), ('user', ip, username)]
            waits = [self.counters[key][0]+600-now for key,limit in zip(keys,[20,5])
                     if key in self.counters and len(self.counters[key]) >= limit]
            if waits: raise LoginLimited(max(1,math.ceil(max(waits))))
            if len(self.counters)+sum(key not in self.counters for key in keys) > self.capacity:
                raise LoginLimited(600)
            for key in keys: self.counters.setdefault(key,deque()).append(now)


login_limiter = LoginLimiter()
