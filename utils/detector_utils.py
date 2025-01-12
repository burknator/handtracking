# Utilities for object detector.

import sys
import os

import numpy as np
import tensorflow as tf
import cv2

from utils import label_map_util

detection_graph = tf.Graph()
sys.path.append("..")

# score threshold for showing bounding boxes.
_score_thresh = 0.27

MODEL_NAME = 'hand_inference_graph'
# Path to frozen detection graph. This is the actual model that is used for the
# object detection.
PATH_TO_CKPT = MODEL_NAME + '/frozen_inference_graph.pb'
# List of the strings that is used to add correct label for each box.
PATH_TO_LABELS = os.path.join(MODEL_NAME, 'hand_label_map.pbtxt')

NUM_CLASSES = 1
# load label map
label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
categories = label_map_util.convert_label_map_to_categories(
    label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
category_index = label_map_util.create_category_index(categories)


# Load a frozen infrerence graph into memory
def load_inference_graph():

    # load frozen tensorflow model into memory
    #print("> ====== loading HAND frozen graph into memory")
    detection_graph = tf.Graph()
    with detection_graph.as_default():
        od_graph_def = tf.GraphDef()
        with tf.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
            serialized_graph = fid.read()
            od_graph_def.ParseFromString(serialized_graph)
            tf.import_graph_def(od_graph_def, name='')
        sess = tf.Session(graph=detection_graph)
    #print(">  ====== Hand Inference graph loaded.")
    return detection_graph, sess


# draw the detected bounding boxes on the images
# You can modify this to also draw a label.
def draw_box_on_image(num_hands_detect, score_thresh, scores, boxes, im_width,
                      im_height, image_np):
    for i in range(num_hands_detect):
        if (scores[i] > score_thresh):
            p1, p2 = box_edges(boxes[i], im_height, im_width)
            cv2.rectangle(image_np, p1, p2, (77, 255, 9), 3, 1)


# Show fps value on image.
def draw_fps_on_image(fps, image_np):
    cv2.putText(image_np, "FPS: {}".format(fps), (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (77, 255, 9), 2)


# Actual detection .. generate scores and bounding boxes given an image
def detect_objects(image_np, detection_graph, sess):
    # Definite input and output Tensors for detection_graph
    image_tensor = detection_graph.get_tensor_by_name('image_tensor:0')
    # Each box represents a part of the image where a particular object was
    # detected.
    detection_boxes = detection_graph.get_tensor_by_name(
        'detection_boxes:0')
    # Each score represent how level of confidence for each of the objects.
    # Score is shown on the result image, together with the class label.
    detection_scores = detection_graph.get_tensor_by_name(
        'detection_scores:0')
    detection_classes = detection_graph.get_tensor_by_name(
        'detection_classes:0')
    num_detections = detection_graph.get_tensor_by_name(
        'num_detections:0')

    image_np_expanded = np.expand_dims(image_np, axis=0)

    (boxes, scores, classes, num) = sess.run(
        [detection_boxes, detection_scores,
            detection_classes, num_detections],
        feed_dict={image_tensor: image_np_expanded})
    return np.squeeze(boxes), np.squeeze(scores)


def box_edges(box, im_height, im_width):
    (left, right, top, bottom) = (box[1] * im_width, box[3] * im_width,
                                  box[0] * im_height, box[2] * im_height)
    p1 = (int(left), int(top))
    p2 = (int(right), int(bottom))
    return p1, p2


def get_center_points(num_hands_detect, score_thresh, scores, boxes, im_width,
                      im_height):
    center_points = []
    for i in range(num_hands_detect):
        if scores[i] <= score_thresh:
            continue

        left_top, right_bottom = box_edges(boxes[i], im_height, im_width)

        center = (left_top[0] + right_bottom[0], left_top[1] + right_bottom[1])
        center = (center[0] / 2, center[1] / 2)

        center_points.append({
            'palm_position': center,
            'box': left_top + right_bottom,
            'confidence': float(scores[i])
        })

    return center_points
