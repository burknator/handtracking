from typing import Tuple, Optional, Type


class VSM:
    init_args: Tuple = ()

    def __init__(self):
        self.states = []
        self.current_state: 'Optional[VSM]' = None
        self.help_text = ""

    def enter(self, parent_state: 'VSM'):
        pass

    @staticmethod
    def _init_state(state: 'Type[VSM]'):
        args = () if not state.init_args else state.init_args
        return state(*args)

    def add(self, state):
        self.states.append(state)

    def enter_state(self, state: 'Type[VSM]'):
        new_state = VSM._init_state(state)
        new_state.enter(self)

        self.current_state = new_state

    def run(self, sm: 'VSM') -> 'Optional[Type[VSM]]':
        if not self.current_state:
            return

        new_state = self.current_state.run(self)

        if new_state:
            self.enter_state(new_state)

        return new_state
