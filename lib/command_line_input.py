from queue import Queue
from threading import Thread


class CommandLineInput:
    def __init__(self):
        self._input_queue = Queue()
        self._thread = Thread(target=self._capture_input, daemon=True)
        self._capturing_not_started_msg = ("You need to start the capturing "
                                           "with `start_capture()` before you "
                                           "can work with the input")

    def _capture_input(self):
        while True:
            input_ = input()
            self._input_queue.put(input_)

    @property
    def is_capturing(self):
        return self._thread.is_alive()

    def start_capture(self):
        if self.is_capturing:
            raise Exception("Capturing already started.")

        self._thread.start()

    def has_input(self):
        if not self.is_capturing:
            raise Exception(self._capturing_not_started_msg)

        return self._input_queue.qsize() > 0

    def get_input(self) -> str:
        if not self.is_capturing:
            raise Exception(self._capturing_not_started_msg)

        return self._input_queue.get()

    def input(self, prompt='') -> str:
        """
        Replaces Python `input()` function in this programm, because of the
        keyboard input capture loop.
        """
        if not self.is_capturing:
            raise Exception(self._capturing_not_started_msg)

        print(prompt, end='', flush=True)
        return self._input_queue.get()
