from threading import Lock
from typing import Generic, TypeVar

T = TypeVar('T')

class SynchronizedVariable(Generic[T]):
    def __init__(self, variable: T = None):
        self._lock = Lock()
        self.value: T = variable

    @property
    def lock(self):
        return self._lock
