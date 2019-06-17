import lib.commandable_state_machine as cmd_state_machine

import state_implementations as states

from .define_aoi_state import DefineAoi
from lib import InvalidTransitionError
from lib.command_line_input import CommandLineInput


class DefineAoiNameState(cmd_state_machine.CommandableStateMachine):
    def __init__(self, cli: CommandLineInput):
        super().__init__()
        self._cli = cli
        self.glad = False

    def enter(self, parent_state: DefineAoi):
        if parent_state.current_state and\
                parent_state.current_state not in [states.InitialState]:
            raise InvalidTransitionError(type(parent_state.current_state), type(self))

        self.help_text = ("You will now define a SINGLE AOI. We start with the "
                    "name, after that select the relevant markers and "
                    "then draw the actual AOI. The program will guide "
                    "you through this process.")

        self._playback_paused = True

        self._register_command(
            key='d',
            description='Save the current AOI name and continue with'
                        'selecting the markers for this AOI.',
            action=lambda: states.DefineAoiMarkerSelectionState
        )

    def run(self, parent_state: DefineAoi):
        if not self.glad:
            if not parent_state.name:
                aoi_name = self._cli.input('Enter name for AOI: ')
                parent_state.name = aoi_name
            else:
                glad = self._cli.input('Are you sure you want to use the name {}? (y/n) '.format(parent_state.name))
                if glad.lower() == 'y':
                    self.glad = True
        else:
            parent_state.enter_state(states.DefineAoiMarkerSelectionState)
