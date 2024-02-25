import threading
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def mutex_wrapper(lock: threading.Lock) -> Callable[[F], F]:
    def wrap(f):
        def func(*args, **kw):
            lock.acquire()
            try:
                return f(*args, **kw)
            finally:
                lock.release()

        return func

    return wrap
