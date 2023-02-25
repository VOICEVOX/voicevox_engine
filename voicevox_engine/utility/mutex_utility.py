import threading


def mutex_wrapper(lock: threading.Lock):
    def wrap(f):
        def func(*args, **kw):
            lock.acquire()
            try:
                return f(*args, **kw)
            finally:
                lock.release()

        return func

    return wrap
