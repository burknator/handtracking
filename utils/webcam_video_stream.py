import cv2

from queue import Queue
from threading import Thread


# Code to thread reading camera input.
# Source : Adrian Rosebrock
# https://www.pyimagesearch.com/2017/02/06/faster-video-file-fps-with-cv2-videocapture-and-opencv/
class WebcamVideoStream:
    def __init__(self, src, width, height, queued=False):
        # initialize the video camera stream and read the first frame
        # from the stream
        self.stream = cv2.VideoCapture(src)

        self.width = width
        self.height = height

        if not queued:
            (self.grabbed, self.frame) = self.stream.read()

        self.queue = Queue() if queued else None

        # initialize the variable used to indicate if the thread should
        # be stopped
        self.stopped = False

    def start(self):
        # start the thread to read frames from the video stream
        Thread(target=self.update, args=()).start()
        return self

    def update(self):
        # keep looping infinitely until the thread is stopped
        while True:
            # if the thread indicator variable is set, stop the thread
            if self.stopped:
                return

            if self.queue:
                grabbed, frame = self.stream.read()

                if not grabbed:
                    self.stop()
                    return

                self.queue.put(self._resize(frame))
            else:
                (self.grabbed, frame) = self.stream.read()

                self.frame = self._resize(frame)

                if not self.grabbed:
                    self.stop()
                    return

    def _resize(self, frame):
        return cv2.resize(frame, (self.width, self.height))

    def read(self):
        # return the frame most recently read
        return self.queue.get() if self.queue else self.frame

    def size(self):
        # return size of the capture device
        return self.stream.get(3), self.stream.get(4)

    def stop(self):
        # indicate that the thread should be stopped
        self.stopped = True
