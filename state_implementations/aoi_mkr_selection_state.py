import cv2

from shapely.geometry import Point, Polygon

import lib.commandable_state_machine as cmd_state_machine

from .define_aoi_state import DefineAoi
from .aoi_draw_state import DefineAoiDrawState
from .aoi_name_state import DefineAoiNameState
from lib import InvalidTransitionError
from lib.opencv_window import OpenCVWindow
from lib.command_line_input import CommandLineInput


class DefineAoiMarkerSelectionState(cmd_state_machine.CommandableStateMachine):
    def __init__(self, window: OpenCVWindow, cli: CommandLineInput):
        super().__init__()

        self.window = window
        self.cli = cli
        self.selections = {}
        self.polygons = {}
        self.define_aoi_state: DefineAoi

    @property
    def help_text(self):
        return ("De-/Select the relevent markers for the AOI {} by "
                "left clicking them.").format(self.aoi_name)

    @help_text.setter
    def help_text(self, text):
        pass

    @property
    def aoi_name(self) -> str:
        return self.define_aoi_state.name

    @property
    def markers(self):
        return self.define_aoi_state.visible_markers.value

    def enter(self, parent_state: DefineAoi):
        if type(parent_state.current_state) not in [DefineAoiDrawState, DefineAoiNameState]:
            raise InvalidTransitionError(type(parent_state.current_state), type(self))

        self.define_aoi_state = parent_state

        for marker in self.markers:
            self.polygons[marker['id']] = Polygon(marker["corners"])
            self.selections[marker['id']] = False

        self.window.set_click_handler(self.select_marker)

        self._register_command(
            key='d',
            description='Save current marker selection and continue to the '
                        'next step.',
            action=self.save_markers_and_continue
        )

    def save_markers_and_continue(self):
        self.define_aoi_state.selected_markers =\
            set(id_ for id_, selected in self.selections.items() if selected)

        print("You selected the markers with the IDs {} for the AOI with name {}".format(self.define_aoi_state.selected_markers, self.aoi_name))

        return DefineAoiDrawState

    def select_marker(self, event, x, y, flags, param):
        if event != cv2.EVENT_LBUTTONDOWN:
            return

        point = Point(x, y)
        for id_, polygon in self.polygons.items():
            if not polygon.contains(point):
                continue

            self.selections[id_] = not self.selections[id_]

            self.cli.print_continuous("selected markers {}".format(self.selections))
