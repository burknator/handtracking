import argparse
import copy

from multiprocessing import Queue
from threading import Thread
from typing import List, Dict

import cv2

from utils import Worker, Calibration
from utils.webcam_video_stream import WebcamVideoStream
from utils.zmq_publisher import HandPositionPublisher, MarkerPublisher
from utils.synchronized_variable import SynchronizedVariable
from lib.state_machine import StateMachine
from lib.command_line_input import CommandLineInput
from lib.opencv_window import OpenCVWindow
from state_implementations.define_aoi_state import DefineAoi
from state_implementations.initial_state import InitialState
from state_implementations.exit_state import ExititingState
from state_implementations.aoi_mkr_selection_state import DefineAoiMarkerSelectionState
from state_implementations.aoi_name_state import DefineAoiNameState
from state_implementations.aoi_draw_state import DefineAoiDrawState

score_thresh = 0.2

if __name__ == '__main__':

    # TODO Add option to generate markers

    parser = argparse.ArgumentParser()
    parser.add_argument('-src', '--source', dest='video_source', type=int,
                        default=0, help='Device index of the camera.')
    parser.add_argument('-img', '--image', dest="image_file", type=open,
                        default=None,
                        help='For debugging purposes, you can provide a path '
                             'to  an image. Setting this will ignore the '
                             'source setting.')
    parser.add_argument('-video', '--video', dest="video_file", type=open,
                        default=None,
                        help='For debugging purposes, you can provide a path '
                             'to a video. Setting this will ignore the source '
                             'setting.')
    parser.add_argument('-nhands', '--num_hands', dest='num_hands', type=int,
                        default=2, help='Max number of hands to detect.')
    parser.add_argument('-fps', '--fps', dest='fps', type=int, default=True,
                        help='Show FPS on detection/display visualization')
    parser.add_argument('-wd', '--width', dest='width', type=int, default=888,
                        help='Width of the frames in the video stream.')
    parser.add_argument('-ht', '--height', dest='height', type=int,
                        default=500,
                        help='Height of the frames in the video stream.')
    parser.add_argument('-ds', '--display', dest='display', type=int,
                        default=True,
                        help='Display the detected images using OpenCV. This '
                        'reduces FPS')
    parser.add_argument('-num-w', '--num-workers', dest='num_workers',
                        type=int, default=4, help='Number of workers.')
    parser.add_argument('-q-size', '--queue-size', dest='queue_size', type=int,
                        default=5, help='Size of the queue.')
    parser.add_argument('-c', '--calibration-file', dest='calibration_file',
                        type=open, default=None,
                        help='Camera calibration file.')
    args = parser.parse_args()

    if args.video_file is not None and args.image_file is not None:
        raise ValueError("Provide either video or image file, not both.")

    input_q = Queue(maxsize=args.queue_size)
    output_q = Queue(maxsize=args.queue_size)

    # No max size here, because this would limit the amount of hand/markers
    # we're able to detect per frame
    center_points_q = Queue()
    marker_q = Queue()

    cap_params = {}

    zmq_publishers = [
        HandPositionPublisher(center_points_q),
        MarkerPublisher(marker_q)
    ]

    for publisher in zmq_publishers:
        publisher.start()

    cap_params['score_thresh'] = score_thresh

    # max number of hands we want to detect/track
    cap_params['num_hands_detect'] = args.num_hands

    def next_image(): return

    def cleanup(): return

    if args.image_file is not None:
        image_file = cv2.imread(args.image_file.name)
        cap_params['im_width'] = image_file.shape[0]
        cap_params['im_height'] = image_file.shape[1]

        def next_image(): return copy.deepcopy(image_file)
    elif args.video_file is not None:
        # If it's a video file, we want the system to take all the time it
        # needs to process every single frame. Thus, the frame from the file
        # are queued and processed one after another. To guarantee that the
        # output is fluid when using a web cam, only the currently captured
        # frame is processed.
        video_capture = WebcamVideoStream(args.video_file.name, args.width,
                                          args.height, queued=True)\
            .start()

        cap_params['im_width'] = args.width
        cap_params['im_height'] = args.height

        def next_image(): return video_capture.read()

        def cleanup(): return video_capture.stop()
    else:
        video_capture = WebcamVideoStream(args.video_source, args.width,
                                          args.height)\
            .start()

        cap_params['im_width'] = args.width
        cap_params['im_height'] = args.height

        def next_image(): return cv2.flip(video_capture.read(), 1)

        def cleanup(): return video_capture.stop()

    if args.calibration_file is not None:
        calibration = Calibration(args.calibration_file)
    else:
        calibration = None

    latest_markers: SynchronizedVariable[List[Dict]] = SynchronizedVariable([])

    for i in range(args.num_workers):
        Thread(target=lambda *args: Worker(*args).run(), daemon=True,
               args=(input_q, output_q, marker_q, center_points_q,
                     cap_params, latest_markers, calibration))\
            .start()

    window = OpenCVWindow('Multi-Threaded Detection')
    window.create()

    def cleanup_():
        print("Stopping ZMQ publishers...")
        for publisher in zmq_publishers:
            publisher.cancel()

        print("Cleaning up...")
        cleanup()

        print("Closing OpenCV windows...")
        window.destroy()

    cli_input = CommandLineInput()
    cli_input.start_capture()

    InitialState.init_args = (next_image, window)
    DefineAoi.init_args = (latest_markers,)
    DefineAoi.initial_state = DefineAoiMarkerSelectionState
    DefineAoiNameState.init_args = (cli_input,)
    DefineAoiMarkerSelectionState.init_args = (window, cli_input)
    DefineAoiDrawState.init_args = (window, cli_input)
    ExititingState.init_args = (cleanup_,)

    state_machine = StateMachine(window, cli_input, input_q, output_q, args.fps,
                                 args.display)

    state_machine.enter_state(InitialState)
    running = True
    while True:
        exit_state = state_machine.run()

        if not running:
            break

        if isinstance(state_machine.current_state, ExititingState):
            running = False
