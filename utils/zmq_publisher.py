import time

from threading import Thread

import zmq, msgpack as serializer

class ZmqPublisher(Thread):
    def __init__(self, q):
        super().__init__()
        self.q = q

        context = zmq.Context()
        self.publish_socket = context.socket(zmq.PUB)
        address = "tcp://127.0.0.1:40002"
        self.publish_socket.connect(address)
        print("Connected to {}".format(address))

    def run(self):
        sensor_packet = {
            "position_source": "camera",
            "palm_position": None,
            "timestamp": None,
            # TODO Use score as calculated by NN
            "confidence": 1.0
        }

        while True:
            data = self.q.get()
            for datum in data:
                # TODO This adds a z-axis value of 0, that probably doesn't make any sense
                sensor_packet["palm_position"] = list(datum) + [0]
                sensor_packet["timestamp"] = self.timestamp()
                self.publish(sensor_packet)

    def publish(self, data):
        payload = serializer.dumps(data)
        self.publish_socket.send_multipart([b"han3", payload])
        print("center points: {}".format(data))

    @staticmethod
    def timestamp():
        return int(round(time.time() * 1000))