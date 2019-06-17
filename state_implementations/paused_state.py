import lib.commandable_state_machine as cmd_state_machine
import lib.state_machine as state_machine


class PausedState(cmd_state_machine.CommandableStateMachine):
    def __init__(self):
        super().__init__()

        self.state_machine: state_machine.StateMachine

    def enter(self, parent_state: 'state_machine.StateMachine'):
        # TODO Stop playback, activate forward (and backward?) frame
        #  skipping

        self._playback_paused = True
        self.state_machine = parent_state

        self._register_command(
            key='p',
            description='Resume playback.',
            action=self.resume
        )

        parent_state._key_handler = self.pause_key_handler

    def resume(self):
        from ..state_implementations.initial_state import InitialState
        self.state_machine._playback_paused = False
        return InitialState

    def pause_key_handler(self, key: str):
        if key == 'j':
            # TODO Previous frame?
            pass
        elif key == 'l':
            # TODO Next frame
            pass
