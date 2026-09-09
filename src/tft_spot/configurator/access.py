"""Serialize snapshot access in the local, single-process API."""

from collections.abc import Callable
from functools import wraps
from threading import RLock

data_lock = RLock()


def data_access[**P, T](function: Callable[P, T]) -> Callable[P, T]:
    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        with data_lock:
            return function(*args, **kwargs)

    return wrapped
