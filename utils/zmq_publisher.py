import time

from threading import Thread

import zmq
import msgpack as serializer


class ZmqPublisher(Thread):
    def __init__(self, q, topic):
        super().__init__()
        self.q = q
        self.topic = topic
        self._cancel = False

        context = zmq.Context()
        self.publish_socket = context.socket(zmq.PUB)
        address = "tcp://127.0.0.1:40002"
        self.publish_socket.connect(address)
        print("Connected to {}".format(address))

    def run(self):
        while True:
            data = self.q.get()
            if self._cancel:
                print("Stopping thread {}", self)
                break
            for datum in data:
                self.publish(self.create_sensor_packet_from_data(datum))

    def publish(self, data):
        self.publish_socket.send_multipart([
            self.topic.encode("ASCII"),
            serializer.dumps(data)
        ])

    def create_sensor_packet_from_data(self, datum):
        raise NotImplementedError("This method needs to be implemented by a "
                                  "sub-class.")

    def cancel(self):
        self._cancel = True
        # If the queue is empty, this thread will be blocked by self.q.get().
        # To unblock it, we need to put an element in.
        if self.q.empty():
            self.q.put(None)

    @staticmethod
    def timestamp():
        return int(round(time.time() * 1000))


class HandPositionPublisher(ZmqPublisher):
    def __init__(self, q):
        super().__init__(q, "han3")

    def create_sensor_packet_from_data(self, datum):
        # TODO This adds a z-axis value of 0 to palm_position, that probably
        #  doesn't make any sense
        return {"position_source": "camera", "palm_position": [0, 0, 0],
                "timestamp": self.timestamp(),
                "confidence": datum['confidence'], "box": datum["box"]}


class MarkerPublisher(ZmqPublisher):
    def __init__(self, q):
        super().__init__(q, "marker")

    def create_sensor_packet_from_data(self, datum):
        return {"corners": datum["corners"], "id": datum["id"],
                "timestamp": self.timestamp()}
