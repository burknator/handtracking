import cv2
import datetime

from enum import Enum
from queue import Queue
from utils import detector_utils
from typing import List, Callable, Tuple

from .command_line_input import CommandLineInput


class State(Enum):
    DEFINE_AOI_MARKERSELECTION = 11
    DEFINE_AOI_DRAW_AOI = 12
    DEFINE_AOI_NAME_AOI = 13
    PAUSED = 2
    INITIAL = 3
    EXITING = 4


class CommandNotFoundException(Exception):
    pass


class InvalidTransitionError(Exception):
    def __init__(self, current_state: State, next_state: State):
        self.start = current_state
        self.end = next_state
        message = "An invalid transition was attempted: {} --> {}"\
                  .format(self.start.name, self.end.name)
        super().__init__(message)


class StateMachine:

    def __init__(self, window_name: str, input_queue: Queue,
                 output_queue: Queue, cli_input: CommandLineInput,
                 display_output=False, draw_fps=False):
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
        self._cli = cli_input
        self._commands = {}

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

    def _register_command(self, key: str, description: str, action: Callable):
        self._commands[key] = (description, action)

    def _check_transition(self, state: State, allowed_origins: List[State]):
        if self.current_state not in allowed_origins:
            raise InvalidTransitionError(self.current_state, state)

    def _get_command(self, command: str) -> Tuple[str, Callable]:
        if command not in self._commands:
            raise CommandNotFoundException("The command {} is not vaild."
                                           .format(command))

        return self._commands[command]

    def _execute_command(self, input_: str):
        """Checks if the input corresponds to a command and executes it."""

        try:
            _, action = self._get_command(input_)
        except CommandNotFoundException:
            # TODO Let the user know, that the input was not a valid command.
            return

        action.execute()

        # Execute any callback which may have been defined by entering a state.
        self._key_handler(input_)

    def _show_help(self, help_text: str):
        if help_text:
            print(help_text)

        for key, content in self._commands.items():
            help_text, _ = content

            if not help_text:
                continue

            print("{}: {}".format(key.upper(), help_text))

        # Ask the user for input. Technically, they could've entered a command
        # at any time. The actual `input`-call which captures this input is in
        # `_start_kbd_capture()`.
        print("Enter a command and press return: ", end="", flush=True)

    def _enter_state(self, state: State):
        msg = "Entering state {}...".format(state.name)
        print('-' * len(msg))
        print(msg)
        print()

        # Reset command list, as each state has it's own commands.
        self._commands = {}

        help_text = ""

        # Define default commands
        self._register_command(
            key='q',
            description="Exit program.",
            action=lambda: self._enter_state(State.EXITING)
        )

        if state != State.INITIAL:
            # The user can only return to the previous state if the program is
            # not in INITIAL.
            self._register_command(
                key='c',
                description="Cancel current operation and go to previous "
                            "state ({}).".format(self._previous_state.name),
                action=lambda: self._return_to_previous_state()
            )

        if state == State.INITIAL:
            # There must be a transition from every state into this one. This
            # makes sense because it basically means we restart the programm,
            # but without the hassle of actually restarting the programm.
            # TODO Start playback

            self._register_command(
                key='p',
                description="Pause playback.",
                action=lambda: self._enter_state(State.PAUSED)
            )

            self._register_command(
                key='a',
                description="Start defining AOI.",
                action=lambda: self._enter_state(State.DEFINE_AOI_MARKERSELECTION)
            )

            def normal_key_handler(key: str):
                pass

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

        elif state == State.DEFINE_AOI_MARKERSELECTION:
            self._check_transition(state, [State.INITIAL,
                                           State.DEFINE_AOI_NAME_AOI,
                                           State.DEFINE_AOI_DRAW_AOI])

            help_text = ("Click on a marker with the LEFT mouse button "
                         "to select it for the current AOI, use the "
                         "RIGHT mouse button to deselect it.")

            # TODO Register click handler for marker selection
            # TODO Left click selects marker, right click deselects marker

            self._register_command(
                key='d',
                description='Save current marker selection and continue to the'
                            'next step.',
                action=lambda: self._enter_state(State.DEFINE_AOI_DRAW_AOI)
            )

            self.current_state = state

        elif state == State.DEFINE_AOI_DRAW_AOI:
            self._check_transition(state, [State.DEFINE_AOI_MARKERSELECTION,
                                           State.DEFINE_AOI_NAME_AOI])

            help_text = ("Use the left mouse button to draw an AOI into "
                         "the window.")

            self._register_command(
                key='d',
                description='Save the current AOI and continue to the next '
                            'step.',
                action=lambda: self._enter_state(State.DEFINE_AOI_NAME_AOI)
            )

            # TODO Register click handler to draw AOI
            # TODO After AOI is drawn, get into NAME_AOI state

            self.current_state = state

        elif state == State.DEFINE_AOI_NAME_AOI:
            self._check_transition(state, [State.DEFINE_AOI_DRAW_AOI])

            aoi_name = self._cli.input('Enter name for AOI: ')
            print("Chosen name: {}".format(aoi_name))

            self._register_command(
                key='d',
                description='Save the current AOI and add another one.',
                action=lambda: self._enter_state(State.DEFINE_AOI_MARKERSELECTION)
            )

            self.current_state = state

        elif state == State.EXITING:
            self._stop = True
            self.current_state = state
            # If the output queue is empty, the main loop of this thread will
            # be blocked, to unblock it, we put a None in it.
            if self.output_queue.empty():
                self.output_queue.put(None)

        self._show_help(help_text)

    def run(self):
        if self.next_image is None:
            raise Exception("You have to define a function which returns "
                            "images (`next_image`).")

        self._start_time = datetime.datetime.now()

        # First, enter initial state. It can register commands which need to
        # be captured by `_cli`.
        self._enter_state(State.INITIAL)

        while True:
            if self._cli.has_input():
                key = self._cli.get_input().lower()
            else:
                key = chr(cv2.waitKey(1) & 0xFF).lower()

            self._execute_command(key)

            if self._stop:
                print("Exiting...")
                break

            # Register any click handler a state may have defined.
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
