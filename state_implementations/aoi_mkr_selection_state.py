import cv2

from shapely.geometry import Point, Polygon

from .define_aoi_state import DefineAoi
from .aoi_draw_state import DefineAoiDrawState
from .aoi_name_state import DefineAoiNameState
import lib.commandable_state_machine as cmd_state_machine
import lib.state_machine as sm

from lib import InvalidTransitionError


class DefineAoiMarkerSelectionState(cmd_state_machine.CommandableStateMachine):
    def __init__(self):
        super().__init__()

        self.selected_markers = {}
        self.markers = {}
        self.marker_polygons = {}
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

    def enter(self, parent_state: DefineAoi):
        if type(parent_state.current_state) not in [DefineAoiDrawState, DefineAoiNameState]:
            raise InvalidTransitionError(type(parent_state.current_state), type(self))

        self.define_aoi_state = parent_state

        self.marker_polygons = {}
        self.selected_markers = {marker["id"]: False for marker in self.markers}
        for marker in parent_state.markers.value:
            self.marker_polygons[marker["id"]] = Polygon(marker["corners"])

        sm.StateMachine._click_handler = self.clicky
        sm.StateMachine.test()

        self._register_command(
            key='d',
            description='Save current marker selection and continue to the'
                        'next step.',
            action=self.save_markers_and_continue
        )

    def save_markers_and_continue(self):
        selected_ids = []
        with self.define_aoi_state.markers.lock:
            for id_, selected in self.selected_markers.items():
                if not selected:
                    continue
                selected_ids.append(id_)
                self.define_aoi_state.markers.value.append(self.markers[id_])

        print("You selected the markers with the IDs {} for the AOI with name {}".format(selected_ids, self.aoi_name))

        return DefineAoiDrawState

    # TODO Register click handler for marker selection
    def clicky(self, event, x, y, flags, param):
        if event != cv2.EVENT_LBUTTONDOWN:
            return

        point = Point(x, y)
        for id, polygon in self.marker_polygons.items():
            if not polygon.contains(point):
                continue

            if self.selected_markers[id]:
                print("deselected marker {}".format(id))
            else:
                print("selected marker {}".format(id))

            self.selected_markers[id] = not self.selected_markers[id]
