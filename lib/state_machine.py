import cv2
import datetime

from typing import Type
from queue import Queue

import lib.commandable_state_machine as cmd_state_machine

from lib.vsm import VSM
from lib.command_line_input import CommandLineInput
import state_implementations as states


class StateMachine(cmd_state_machine.CommandableStateMachine):
    _key_handler = lambda key: ()
    _click_handler = lambda *args: ()
    test = lambda: ()

    def __init__(self, window_name, cli_input: CommandLineInput,
                 input_queue: Queue, output_queue: Queue, draw_fps=False,
                 display_output=False):
        super().__init__()

        self.window_name = window_name
        self.cleanup = lambda: ()
        self.next_image = None


        self._stop = False
        self._cli = cli_input
        self._start_time = datetime.datetime.now()
        self._num_frames = 0

        self.input_queue = input_queue
        self.output_queue = output_queue
        self.display_output = display_output
        self.draw_fps = draw_fps

        StateMachine.test = lambda: cv2.setMouseCallback(self.window_name, StateMachine._click_handler)

    def _get_elapsed_time(self):
        return (datetime.datetime.now() - self._start_time).total_seconds()

    def _get_fps(self):
        elapsed_time = self._get_elapsed_time()
        return self._num_frames / elapsed_time, elapsed_time

    def _return_to_previous_state(self):
        raise NotImplementedError()

    def enter_state(self, state: Type[VSM]):
        super().enter_state(state)

        # Define default commands
        self._register_command(
            key='q',
            description="Exit program.",
            action=lambda: states.ExititingState
        )

        if not isinstance(state, type(states.InitialState)):
            # The user can only return to the previous state if the program is
            # not in INITIAL.
            self._register_command(
                key='c',
                description="Cancel current operation and go to previous "
                            "state ({}).".format("STATE"),
                action=lambda: self._return_to_previous_state()
            )

        if self.current_state:
            self._show_help(self.current_state.help_text)

    def run(self, sm=None):
        if self._cli.has_input():
            key = self._cli.get_input().lower()
        else:
            key = chr(cv2.waitKey(1) & 0xFF).lower()

        new_state = self._execute_command(key)

        if new_state and isinstance(new_state, type(VSM)):
            self.enter_state(new_state)
            return new_state

        if StateMachine._key_handler:
            StateMachine._key_handler(key)

        return super().run(self)
