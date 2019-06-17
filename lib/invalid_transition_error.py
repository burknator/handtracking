from typing import Type

from lib.vsm import VSM


class InvalidTransitionError(Exception):
    def __init__(self, current_state: Type[VSM], next_state: Type[VSM]):
        self.start = current_state
        self.end = next_state
        message = "An invalid transition was attempted: {} --> {}"\
                  .format(self.start, self.end)
        super().__init__(message)
