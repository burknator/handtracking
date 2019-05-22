import copy

from typing import Dict, Any
from queue import Queue
from threading import Lock, Thread

from cv2 import aruco

from .detector_utils import load_inference_graph, detect_objects, get_center_points,\
    draw_box_on_image
from .calibration import Calibration

# 117 was found out by testing with static test-images. The real number of the markers created by
#  the Pupil team is not known/does not work
#  (see https://github.com/pupil-labs/pupil-helpers/tree/master/markers_stickersheet).
_aruco_dict = aruco.Dictionary_create(117, 3)
_aruco_parameters = aruco.DetectorParameters_create()

class Worker:
    def __init__(self, input_q: Queue, output_q: Queue, marker_q: Queue, center_points_q: Queue,
        cap_params: Dict[str, Any], calibration: Calibration):
        self.input_q = input_q
        self.output_q = output_q
        self.marker_q = marker_q
        self.center_points_q = center_points_q
        self.cap_params = cap_params
        self.calibration = calibration
        self.detection_graph, self.sess = load_inference_graph()

    def _detect_hands(self, frame, o_frame, lock):
        # Actual detection. Variable boxes contains the bounding box coordinates for hands detected,
        # while scores contains the confidence for each of these boxes.
        # Hint: If len(boxes) > 1 , you may assume you have found at least one hand (within your
        # score threshold)

        boxes, scores = detect_objects(frame, self.detection_graph, self.sess)

        hand_center_points = get_center_points(self.cap_params["num_hands_detect"],
                                                self.cap_params["score_thresh"],
                                                scores, boxes,
                                                self.cap_params["im_width"],
                                                self.cap_params["im_height"])

        self.center_points_q.put(hand_center_points)
        print("center points: {}".format(hand_center_points))

        with lock:
            draw_box_on_image(
                self.cap_params['num_hands_detect'], self.cap_params["score_thresh"],
                scores, boxes, self.cap_params['im_width'], self.cap_params['im_height'],
                o_frame)

    def _detect_markers(self, frame, o_frame, lock):
        corners, ids, _ = aruco.detectMarkers(frame, _aruco_dict,
                                              parameters=_aruco_parameters)

        if ids is not None:
            markers = []
            for i in range(len(corners)):
                markers.append({
                    'id': int(ids[i][0]),
                    'corners': corners[i][0].astype(int).tolist(),
                })
            self.marker_q.put(markers)

            with lock:
                aruco.drawDetectedMarkers(o_frame, corners, ids)

            rotation_vecs, translation_vecs, _ = aruco.estimatePoseSingleMarkers(corners, self.calibration.ml, self.calibration.camera_matrix, self.calibration.dist_coeffs)

            with lock:
                for i in range(len(ids)):
                    aruco.drawAxis(o_frame, self.calibration.camera_matrix, self.calibration.dist_coeffs, rotation_vecs[i], translation_vecs[i], 0.01)

    def run(self):
        while True:
            frame = self.input_q.get()

            if frame is None:
                self.output_q.put(frame)
                continue

            # Create copy of frame to draw boxes on (we don't want to draw that on the input frame,
            # because either of the detection algorithms could be disturbed by this).
            o_frame = copy.deepcopy(frame)

            lock = Lock()

            threads = []
            for method in [self._detect_hands, self._detect_markers]:
                thr = Thread(target=method, args=(frame, o_frame, lock))
                thr.start()
                threads.append(thr)

            for thread in threads:
                thread.join()

            self.output_q.put(o_frame)

            # TODO Get translation matrices and draw AOI on image, BUT HOW DO GET AOI HERE?
