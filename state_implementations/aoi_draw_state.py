import lib.commandable_state_machine as cmd_state_machine

from lib import InvalidTransitionError
from lib.vsm import VSM

import state_implementations as states


class DefineAoiDrawState(cmd_state_machine.CommandableStateMachine):
    def enter(self, parent_state: VSM):
        if parent_state.current_state not in [states.DefineAoiMarkerSelectionState, states.DefineAoiNameState]:
            raise InvalidTransitionError(type(parent_state.current_state), type(self))

        self.help_text = ("Use the left mouse button to draw an AOI into "
                          "the window.")

        self._register_command(
            key='d',
            description='Save the current AOI and continue to the next '
                        'step.',
            action=lambda: states.DefineAoiNameState
        )

        # TODO Register click handler to draw AOI
        # TODO After AOI is drawn, get into NAME_AOI state
