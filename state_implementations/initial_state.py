import cv2
import datetime

import lib.state_machine as stt_mhn
import lib.commandable_state_machine as cmd_state_machine
import utils.detector_utils as detector_utils

import state_implementations as states


class InitialState(cmd_state_machine.CommandableStateMachine):
    def __init__(self, next_image):
        super().__init__()

        self.next_image = next_image

        self._start_time = datetime.datetime.now()
        self._num_frames = 0

    def enter(self, parent_state: 'stt_mhn.StateMachine'):
        # There must be a transition from every state into this one. This
        # makes sense because it basically means we restart the programm,
        # but without the hassle of actually restarting the programm.
        # TODO Start playback

        if self.next_image is None:
            raise Exception("You have to define a function which returns "
                            "images (`next_image`).")

        self._start_time = datetime.datetime.now()

        self._register_command(
            key='p',
            description="Pause playback.",
            action=lambda: states.PausedState
        )

        self._register_command(
            key='a',
            description="Start defining AOI.",
            action=lambda: states.DefineAoi
        )

    def run(self, parent_state):
        frame = self.next_image()
        self._num_frames += 1

        parent_state.input_queue.put(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        output_frame = parent_state.output_queue.get()

        # TODO Log queue length

        if output_frame is None:
            print("Received empty output frame, exiting...")
            return states.ExititingState

        output_frame = cv2.cvtColor(output_frame, cv2.COLOR_RGB2BGR)

        fps, elapsed_time = parent_state._get_fps()

        if parent_state.display_output:
            if parent_state.draw_fps:
                detector_utils.draw_fps_on_image(fps, output_frame)
            cv2.imshow(parent_state.window_name, output_frame)
        else:
            print("frames processed: {}, elapsed time: {}, fps: {}"
                  .format(self._num_frames, elapsed_time, fps))
