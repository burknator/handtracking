import cv2

from typing import List, Tuple

import lib.commandable_state_machine as cmd_state_machine
import state_implementations as states

from lib import InvalidTransitionError
from lib.vsm import VSM
from lib.opencv_window import OpenCVWindow
from lib.command_line_input import CommandLineInput
from .define_aoi_state import DefineAoi


class DefineAoiDrawState(cmd_state_machine.CommandableStateMachine):
    def __init__(self, window: OpenCVWindow, cli: CommandLineInput):
        super().__init__()
        self.window = window
        self.cli = cli
        self.selected_points: List[Tuple[int, int]] = []

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

        self._register_command(
            key='r',
            description='Delete all selected points.',
            action=lambda: self.selected_points.clear()
        )

        self.window.set_click_handler(self.add_point)

        # TODO After AOI is drawn, get into NAME_AOI state

    def add_point(self, event, x, y, flags, param):
        if event != cv2.EVENT_LBUTTONDOWN:
            return

        self.selected_points.append((x, y))
        self.selected_points = self.selected_points[-4:]

        self.cli.print_continuous("Selected points: {}".format(self.selected_points))

    def run(self, parent_state: DefineAoi):
        # TODO Draw rectangle on image
        pass
