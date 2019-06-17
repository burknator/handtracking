from typing import Callable

import lib.state_machine as state_machine
import lib.vsm as vsm


class ExititingState(vsm.VSM):
    def __init__(self, cleanup: Callable):
        super().__init__()
        self.cleanup = cleanup

    def run(self, sm: 'state_machine.StateMachine'):
        # If the output queue is empty, the main loop of this thread will
        # be blocked, to unblock it, we put a None in it.
        if sm.output_queue.empty():
            sm.output_queue.put(None)

        fps, _ = sm._get_fps()
        print("FPS:", fps)

        self.cleanup()
