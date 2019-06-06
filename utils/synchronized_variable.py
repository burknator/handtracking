from threading import Lock
from typing import Generic, TypeVar

T = TypeVar('T')

class SynchronizedVariable(Generic[T]):
    def __init__(self, variable: T):
        self._lock = Lock()
        self._value = variable

    @property
    def lock(self):
        return self._lock

    @property
    def value(self) -> T:
        return self._value

    @value.setter
    def value(self, new_value: T) -> T:
        with self.lock:
            self._value = new_value
