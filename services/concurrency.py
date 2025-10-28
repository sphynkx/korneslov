import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict


## Read from config if available, otherwise from env with defaults
try:
    from config import AI_MAX_CONCURRENT as _AI_MAX_CONCURRENT  # type: ignore
except Exception:
    _AI_MAX_CONCURRENT = int(os.getenv("AI_MAX_CONCURRENT", "2"))

try:
    from config import TG_SEND_MAX_CONCURRENT as _TG_SEND_MAX_CONCURRENT  ## type: ignore
except Exception:
    _TG_SEND_MAX_CONCURRENT = int(os.getenv("TG_SEND_MAX_CONCURRENT", "4"))

## Global semaphores
_AI_SEM = asyncio.Semaphore(_AI_MAX_CONCURRENT)
_SEND_SEM = asyncio.Semaphore(_TG_SEND_MAX_CONCURRENT)

## Per-user locks to serialize processing for the same user
_USER_LOCKS: Dict[int, asyncio.Lock] = {}
_USER_LOCKS_LOCK = asyncio.Lock()


async def _get_user_lock(uid: int) -> asyncio.Lock:
    async with _USER_LOCKS_LOCK:
        lock = _USER_LOCKS.get(uid)
        if lock is None:
            lock = asyncio.Lock()
            _USER_LOCKS[uid] = lock
        return lock


@asynccontextmanager
async def acquire_ai():
    await _AI_SEM.acquire()
    try:
        yield
    finally:
        _AI_SEM.release()


@asynccontextmanager
async def acquire_send():
    await _SEND_SEM.acquire()
    try:
        yield
    finally:
        _SEND_SEM.release()


@asynccontextmanager
async def acquire_user_lock(uid: int):
    lock = await _get_user_lock(uid)
    await lock.acquire()
    try:
        yield
    finally:
        lock.release()
