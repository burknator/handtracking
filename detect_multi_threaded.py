import datetime, argparse, copy

from multiprocessing import Queue, Pool

import cv2
from cv2 import aruco

from utils import detector_utils as detector_utils, Worker, Calibration
from utils.detector_utils import WebcamVideoStream
from utils.zmq_publisher import HandPositionPublisher, MarkerPublisher

score_thresh = 0.2

def worker(*args):
    Worker(*args).run()


if __name__ == '__main__':

    # TODO Add option to generate markers

    parser = argparse.ArgumentParser()
    parser.add_argument('-src', '--source', dest='video_source', type=int, default=0,
                        help='Device index of the camera.')
    parser.add_argument('-img', '--image', dest="image_file", type=open, default=None,
                        help='For debugging purposes, you can provide a path to an image. Setting'
                             'this will ignore the source setting.')
    parser.add_argument('-video', '--video', dest="video_file", type=open, default=None,
                        help='For debugging purposes, you can provide a path to a video. Setting'
                             'this will ignore the source setting.')
    parser.add_argument('-nhands', '--num_hands', dest='num_hands', type=int, default=2,
                        help='Max number of hands to detect.')
    parser.add_argument('-fps', '--fps', dest='fps', type=int, default=1,
                        help='Show FPS on detection/display visualization')
    parser.add_argument('-wd', '--width', dest='width', type=int, default=888,
                        help='Width of the frames in the video stream.')
    parser.add_argument('-ht', '--height', dest='height', type=int, default=500,
                        help='Height of the frames in the video stream.')
    parser.add_argument('-ds', '--display', dest='display', type=int, default=1,
                        help='Display the detected images using OpenCV. This reduces FPS')
    parser.add_argument('-num-w', '--num-workers', dest='num_workers', type=int, default=4,
                        help='Number of workers.')
    parser.add_argument('-q-size', '--queue-size', dest='queue_size', type=int, default=5,
                        help='Size of the queue.')
    parser.add_argument('-c', '--calibration-file', dest='calibration_file', type=open,
                        default=None, help='Camera calibration file.')
    args = parser.parse_args()

    if args.video_file is not None and args.image_file is not None:
        raise ValueError("Provide either video or image file, not both.")

    input_q = Queue(maxsize=args.queue_size)
    output_q = Queue(maxsize=args.queue_size)

    # No max size here, because this would limit the amount of hand/markers we're able to detect per
    # frame
    center_points_q = Queue()
    marker_q = Queue()

    cap_params = {}

    HandPositionPublisher(center_points_q).start()
    MarkerPublisher(marker_q).start()

    cap_params['score_thresh'] = score_thresh

    # max number of hands we want to detect/track
    cap_params['num_hands_detect'] = args.num_hands

    print(cap_params, args)

    next_image = None
    cleanup = None

    if args.image_file is not None:
        image_file = cv2.imread(args.image_file.name)
        cap_params['im_width'], cap_params['im_height'] = image_file.shape[0], image_file.shape[1]

        next_image = lambda: copy.deepcopy(image_file)
        cleanup = lambda: args.image_file.close()
    elif args.video_file is not None:
        # If it's a video file, we want the system to take all the time it needs to process every
        # single frame. Thus, the frame from the file are queued and processed one after another.
        # To guarantee that the output is fluid when using a web cam, only the currently captured
        # frame is processed.
        video_capture = WebcamVideoStream(args.video_file.name, args.width, args.height, queued=True)\
            .start()

        cap_params['im_width'], cap_params['im_height'] = args.width, args.height

        next_image = lambda: video_capture.read()
        cleanup = lambda: video_capture.stop()
    else:
        video_capture = WebcamVideoStream(args.video_source, args.width, args.height)\
            .start()

        cap_params['im_width'], cap_params['im_height'] = args.width, args.height

        next_image = lambda: cv2.flip(video_capture.read(), 1)
        cleanup = lambda: video_capture.stop()

    if next_image is None or cleanup is None:
        raise RuntimeError("Something went deeply wrong.")

    if args.calibration_file is not None:
    calibration = Calibration(args.calibration_file)
    else:
        calibration = None

    worker_pool = Pool(args.num_workers, worker,
                       (input_q, output_q, marker_q, center_points_q, cap_params, calibration))

    start_time = datetime.datetime.now()
    num_frames = 0
    fps = 0
    index = 0

    cv2.namedWindow('Multi-Threaded Detection', cv2.WINDOW_NORMAL)

    while True:
        frame = next_image()
        index += 1

        input_q.put(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        output_frame = output_q.get()

        output_frame = cv2.cvtColor(output_frame, cv2.COLOR_RGB2BGR)

        elapsed_time = (datetime.datetime.now() - start_time).total_seconds()
        num_frames += 1
        fps = num_frames / elapsed_time
        # print("frame ",  index, num_frames, elapsed_time, fps)

        if output_frame is not None:
            if args.display > 0:
                if args.fps > 0:
                    detector_utils.draw_fps_on_image("FPS : " + str(int(fps)),
                                                     output_frame)
                cv2.imshow('Multi-Threaded Detection', output_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                if num_frames == 400:
                    num_frames = 0
                    start_time = datetime.datetime.now()
                else:
                    print("frames processed: ", index, "elapsed time: ",
                          elapsed_time, "fps: ", str(int(fps)))
        else:
            # print("video end")
            break
    elapsed_time = (datetime.datetime.now() - start_time).total_seconds()
    fps = num_frames / elapsed_time
    print("fps", fps)
    worker_pool.terminate()
    cleanup()
    cv2.destroyAllWindows()
