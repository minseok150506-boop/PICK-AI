from __future__ import annotations
import os, threading, time
from contextlib import contextmanager

class InferenceBusy(RuntimeError): pass
class CircuitOpen(RuntimeError): pass

class InferenceGuard:
    def __init__(self):
        self.max_concurrent=max(1,int(os.environ.get("PICK_MAX_CONCURRENT_AI","1")))
        self.wait_seconds=max(5,int(os.environ.get("PICK_AI_QUEUE_WAIT_SECONDS","90")))
        self.failure_threshold=max(2,int(os.environ.get("PICK_AI_FAILURE_THRESHOLD","4")))
        self.cooldown_seconds=max(10,int(os.environ.get("PICK_AI_COOLDOWN_SECONDS","45")))
        self._sem=threading.BoundedSemaphore(self.max_concurrent)
        self._lock=threading.Lock(); self._active=0; self._waiting=0; self._failures=0; self._open_until=0.0
    def status(self):
        with self._lock:
            return {"active":self._active,"waiting":self._waiting,"max_concurrent":self.max_concurrent,
                    "failures":self._failures,"circuit_open":time.monotonic()<self._open_until,
                    "cooldown_remaining":max(0,round(self._open_until-time.monotonic(),1))}
    def _check(self):
        with self._lock:
            if time.monotonic()<self._open_until: raise CircuitOpen("AI 서버가 연속 오류 후 잠시 복구 대기 중입니다.")
    def success(self):
        with self._lock: self._failures=0; self._open_until=0.0
    def failure(self):
        with self._lock:
            self._failures+=1
            if self._failures>=self.failure_threshold:self._open_until=time.monotonic()+self.cooldown_seconds
    @contextmanager
    def slot(self):
        self._check()
        with self._lock:self._waiting+=1
        ok=self._sem.acquire(timeout=self.wait_seconds)
        with self._lock:self._waiting-=1
        if not ok: raise InferenceBusy("AI 요청이 많습니다. 잠시 후 다시 시도해 주세요.")
        with self._lock:self._active+=1
        try:self._check(); yield
        finally:
            with self._lock:self._active=max(0,self._active-1)
            self._sem.release()
guard=InferenceGuard()
