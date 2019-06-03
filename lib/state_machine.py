import cv2
import datetime

from enum import Enum
from queue import Queue
from utils import detector_utils


class State(Enum):
    DEFINE_AOI = 1
    DEFINE_AOI_MARKERSELECTION = 11
    DEFINE_AOI_DRAW_AOI = 12
    DEFINE_AOI_NAME_AOI = 13
    PAUSED = 2
    INITIAL = 3
    EXITING = 4


class InvalidTransitionError(Exception):
    def __init__(self, current_state: State, next_state: State):
        self.start = current_state
        self.end = next_state
        message = "An invalid transition was attempted: {} --> {}"\
                  .format(self.start.name, self.end.name)
        super().__init__(message)


class StateMachine:

    def __init__(self, window_name: str, input_queue: Queue,
                 output_queue: Queue, display_output=False, draw_fps=False):
        self.window_name = window_name
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.display_output = display_output
        self.draw_fps = draw_fps

        self.cleanup = lambda: ()
        self.next_image = None

        self._current_state = State.INITIAL
        self._previous_state = State.INITIAL
        self._start_time = datetime.datetime.now()
        self._num_frames = 0
        self._click_handler = lambda event, x, y, flags, param: ()
        self._key_handler = lambda key: ()
        self._stop = False
        self._help_text = ""

    @property
    def current_state(self):
        return self._current_state

    @current_state.setter
    def current_state(self, state: State):
        self._previous_state = self._current_state
        self._current_state = state

    def exit(self):
        fps, _ = self._get_fps()
        print("FPS:", fps)

        self.cleanup()

    def _get_elapsed_time(self):
        return (datetime.datetime.now() - self._start_time).total_seconds()

    def _get_fps(self):
        elapsed_time = self._get_elapsed_time()
        return self._num_frames / elapsed_time, elapsed_time

    def _return_to_previous_state(self):
        try:
            self._enter_state(self._previous_state)
        except InvalidTransitionError as e:
            if e.end != State.INITIAL:
                # Try to enter the initial state if the previous state could
                # not be entered.
                self._enter_state(State.INITIAL)
            else:
                # If we already tried to enter the initial state, but failed at
                # that, we raise an exception, because the initial state must
                # always be enterable.
                raise Exception("Tried to re-enter the initial state {}, but "
                                "it didn't work, although it should've."
                                .format(e.end.name))

    def _enter_state(self, state: State):
        print("Entering state {}...".format(state.name))

        """
        Zustände:
        1. AOI bestimmen
            1. Markerselektion
            2. AOI per Maus ins Bild ziehen (als Rechteck erst mal)
            3. Zurück zu Schritt 1.1 oder abbrechen
        2. Pausiert
            Bei Video und Webcam einfach Bild einfrieren. Bei Video zusätzlich
             Bild für Bild durchschalten können.
        3. Normal
        """

        if state == State.INITIAL:
            # There must be a transition from every state into this one. This
            # makes sense because it basically means we restart the programm,
            # but without the hassle of actually restarting the programm.
            # TODO Start playback

            self._help_text = ""

            def normal_key_handler(key: str):
                if key == 'p':
                    self._enter_state(State.PAUSED)

                elif key == 'a':
                    self._enter_state(State.DEFINE_AOI)

            self._click_handler = lambda *args: ()
            self._key_handler = normal_key_handler

            self.current_state = state
        elif state == State.PAUSED:
            # TODO Stop playback, activate forward (and backward?) frame
            #  skipping
            def pause_key_handler(key: str):
                if key == 'j':
                    # TODO Previous frame?
                    pass
                elif key == 'l':
                    # TODO Next frame
                    pass

            self._click_handler = lambda *args: ()
            self._key_handler = pause_key_handler

            self.current_state = state
        elif state == State.DEFINE_AOI:
            # TODO Pause playback, essentially activate pause state
            self._click_handler = lambda *args: ()

            # Directly jump into marker selection
            self._enter_state(State.DEFINE_AOI_MARKERSELECTION)
        elif state == State.DEFINE_AOI_MARKERSELECTION:
            if self.current_state not in [State.DEFINE_AOI,
                                          State.DEFINE_AOI_DRAW_AOI]:
                raise InvalidTransitionError(self.current_state, state)

            # TODO Register click handler for marker selection
            # TODO Left click selects marker, right click deselects marker

            self.current_state = state
        elif state == State.DEFINE_AOI_DRAW_AOI:
            if self.current_state not in [State.DEFINE_AOI_MARKERSELECTION,
                                          State.DEFINE_AOI_NAME_AOI]:
                raise InvalidTransitionError(self.current_state, state)

            # TODO Register click handler to draw AOI
            # TODO After AOI is drawn, get into NAME_AOI state

            self.current_state = state
        elif state == State.DEFINE_AOI_NAME_AOI:
            if self.current_state != State.DEFINE_AOI_DRAW_AOI:
                raise InvalidTransitionError(self.current_state, state)

            # TODO Ask user for name of AOI

            self.current_state = state
        elif state == State.EXITING:
            self._stop = True
            self.current_state = state
            # If the output queue is empty, the main loop of this thread will
            # be blocked
            if self.output_queue.empty():
                self.output_queue.put(None)

        print(self._help_text)

    def run(self):
        if self.next_image is None:
            raise Exception("You have to define a function which returns "
                            "images (`next_image`).")

        self._start_time = datetime.datetime.now()

        self._enter_state(State.INITIAL)

        while True:
            key = chr(cv2.waitKey(1) & 0xFF).lower()

            if key == 'q':
                self._enter_state(State.EXITING)
            elif key == 'c':
                self._return_to_previous_state()

            # TODO Also handle pressed keys in console!!
            self._key_handler(key)

            if self._stop:
                print("Exiting...")
                break

            cv2.setMouseCallback(self.window_name, self._click_handler)

            frame = self.next_image()
            self._num_frames += 1

            self.input_queue.put(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

            output_frame = self.output_queue.get()

            # TODO Log queue length

            if output_frame is None:
                print("Received empty output frame, exiting...")
                break

            output_frame = cv2.cvtColor(output_frame, cv2.COLOR_RGB2BGR)

            fps, elapsed_time = self._get_fps()

            if self.display_output:
                if self.draw_fps:
                    detector_utils.draw_fps_on_image(fps, output_frame)
                cv2.imshow(self.window_name, output_frame)
            else:
                print("frames processed: {}, elapsed time: {}, fps: {}"
                      .format(self._num_frames, elapsed_time, fps))

        self.exit()
