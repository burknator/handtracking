import cv2

from typing import Callable


class OpenCVWindow:
    def __init__(self, name):
        self.name = name

    def _dummy_click_handler(self, *args):
        pass

    def create(self, type_=cv2.WINDOW_NORMAL):
        cv2.namedWindow(self.name, type_)

    def unset_click_handler(self):
        self.set_click_handler(self._dummy_click_handler)

    def set_click_handler(self, handler: Callable):
        cv2.setMouseCallback(self.name, handler)

    def get_pressed_key(self):
        return chr(cv2.waitKey(1) & 0xFF)

    def show_frame(self, frame):
        cv2.imshow(self.name, frame)

    def destroy(self):
        cv2.destroyAllWindows()

        # Workaround for not closing windows
        # (source: https://stackoverflow.com/a/50538883)
        for i in range(5):
            cv2.waitKey(1)
