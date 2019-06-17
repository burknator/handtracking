from typing import List, Dict

import lib.commandable_state_machine as cmd_state_machine
import state_implementations as states

from utils.synchronized_variable import SynchronizedVariable


class DefineAoi(cmd_state_machine.CommandableStateMachine):
    def __init__(self, markers: SynchronizedVariable[List[Dict]]):
        super().__init__()
        self.name = ""
        self.markers = markers

    def enter(self, sm):
        self._register_command(
            key='t',
            description="Ich bin ein Test",
            action=lambda: states.InitialState
        )

        self.enter_state(states.DefineAoiNameState)
