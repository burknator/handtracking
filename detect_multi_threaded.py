import datetime, argparse, copy

from multiprocessing import Queue, Pool

import cv2
import cv2.aruco as aruco

from utils import detector_utils as detector_utils
from utils.detector_utils import WebcamVideoStream
from utils.zmq_publisher import HandPositionPublisher, MarkerPublisher

frame_processed = 0
score_thresh = 0.2

# 117 was found out by testing with static test-images. The real number of the markers created by
#  the Pupil team is not known/does not work
#  (see https://github.com/pupil-labs/pupil-helpers/tree/master/markers_stickersheet).
aruco_dict = aruco.Dictionary_create(117, 3)
parameters = aruco.DetectorParameters_create()


def worker(input_q, output_q, marker_q, center_points_q, cap_params):
    detection_graph, sess = detector_utils.load_inference_graph()

    while True:
        frame = input_q.get()

        if frame is None:
            output_q.put(frame)
            continue

        # Create copy of frame to draw boxes on (we don't want to draw that on the input frame,
        # because either of the detection algorithms could be disturbed by this).
        o_frame = copy.deepcopy(frame)

        # Actual detection. Variable boxes contains the bounding box coordinates for hands detected,
        # while scores contains the confidence for each of these boxes.
        # Hint: If len(boxes) > 1 , you may assume you have found at least one hand (within your
        # score threshold)

        boxes, scores = detector_utils.detect_objects(frame, detection_graph, sess)

        hand_center_points = detector_utils.get_center_points(cap_params["num_hands_detect"],
                                                              cap_params["score_thresh"],
                                                              scores, boxes,
                                                              cap_params["im_width"],
                                                              cap_params["im_height"])

        center_points_q.put(hand_center_points)
        print("center points: {}".format(hand_center_points))

        detector_utils.draw_box_on_image(
            cap_params['num_hands_detect'], cap_params["score_thresh"],
            scores, boxes, cap_params['im_width'], cap_params['im_height'],
            o_frame)

        corners, ids, _ = aruco.detectMarkers(frame, aruco_dict,
                                              parameters=parameters)

        markers = []
        for i in range(len(corners)):
            markers.append({
                'id': int(ids[i][0]),
                'corners': corners[i][0].astype(int).tolist(),
            })
        marker_q.put(markers)

        aruco.drawDetectedMarkers(o_frame, corners, ids)

        output_q.put(o_frame)

        # TODO Get translation matrices and draw AOI on image, BUT HOW DO GET AOI HERE?

    sess.close()


if __name__ == '__main__':

    # TODO Add option to generate markers

    parser = argparse.ArgumentParser()
    parser.add_argument('-src', '--source', dest='video_source', type=int, default=0,
                        help='Device index of the camera.')
    parser.add_argument('-img', '--image', dest="image_file", type=open, default=None,
                        help='For debugging purposes, you can provide a path to an image. Setting'
                             'this will ignore the source setting.')
    parser.add_argument('-nhands', '--num_hands', dest='num_hands', type=int, default=2,
                        help='Max number of hands to detect.')
    parser.add_argument('-fps', '--fps', dest='fps', type=int, default=1,
                        help='Show FPS on detection/display visualization')
    parser.add_argument('-wd', '--width', dest='width', type=int, default=504,
                        help='Width of the frames in the video stream.')
    parser.add_argument('-ht', '--height', dest='height', type=int, default=504,
                        help='Height of the frames in the video stream.')
    parser.add_argument('-ds', '--display', dest='display', type=int, default=1,
                        help='Display the detected images using OpenCV. This reduces FPS')
    parser.add_argument('-num-w', '--num-workers', dest='num_workers', type=int, default=4,
                        help='Number of workers.')
    parser.add_argument('-q-size', '--queue-size', dest='queue_size', type=int, default=5,
                        help='Size of the queue.')
    args = parser.parse_args()

    input_q = Queue(maxsize=args.queue_size)
    output_q = Queue(maxsize=args.queue_size)

    # No max size here, because this would limit the amount of hand/markers we're able to detect per
    # frame
    center_points_q = Queue()
    marker_q = Queue()

    cap_params = {}
    frame_processed = 0

    HandPositionPublisher(center_points_q).start()
    MarkerPublisher(marker_q).start()

    cap_params['score_thresh'] = score_thresh

    # max number of hands we want to detect/track
    cap_params['num_hands_detect'] = args.num_hands

    print(cap_params, args)

    if args.image_file is not None:
        image_file = cv2.imread(args.image_file.name)
        cap_params['im_width'], cap_params['im_height'] = image_file.shape[0], image_file.shape[1]


        def next_image():
            return copy.deepcopy(image_file)


        def cleanup():
            args.image_file.close()
    else:
        video_capture = WebcamVideoStream(src=args.video_source, width=args.width,
                                          height=args.height).start()

        cap_params['im_width'], cap_params['im_height'] = video_capture.size()


        def next_image():
            frame = video_capture.read()
            frame = cv2.flip(frame, 1)
            return frame


        def cleanup():
            video_capture.stop()

    worker_pool = Pool(args.num_workers, worker,
                       (input_q, output_q, marker_q, center_points_q, cap_params))

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
