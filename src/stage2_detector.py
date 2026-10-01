import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray
from ultralytics import YOLO


class YoloDetector(Node):
    def __init__(self):
        super().__init__("yolo_detector")

        self.declare_parameter("conf", 0.5)

        self.model = YOLO("yolov8n.pt")

        self.cap = cv2.VideoCapture(0)

        if not self.cap.isOpened():
            self.get_logger().error("Camera open nahi hui")
            return

        self.img_pub = self.create_publisher(
            Image,
            "/image_annotated",
            10
        )

        self.det_pub = self.create_publisher(
            Float32MultiArray,
            "/detections",
            10
        )

        self.create_timer(0.03, self.loop)

    def loop(self):

        ok, frame = self.cap.read()

        if not ok:
            self.get_logger().warn("Frame nahi mila")
            return

        # Mirror view
        frame = cv2.flip(frame, 1)

        h, w = frame.shape[:2]

        # YOLO detection
        results = self.model(
            frame,
            conf=self.get_parameter("conf").value,
            classes=[0],
            verbose=False
        )[0]

        # Detection data publish
        data = [float(w), float(h)]

        for box in results.boxes:

            x1, y1, x2, y2 = box.xyxy[0].tolist()

            data += [
                (x1 + x2) / 2,
                (y1 + y2) / 2,
                x2 - x1,
                y2 - y1,
                float(box.conf[0]),
                float(box.cls[0])
            ]

        det = Float32MultiArray()
        det.data = data

        self.det_pub.publish(det)

        # Draw boxes
        annotated = results.plot()

        # SHOW CAMERA WINDOW
        cv2.imshow("YOLO Camera", annotated)
        cv2.waitKey(1)

        # Publish ROS image
        img = Image()
        img.header.stamp = self.get_clock().now().to_msg()
        img.header.frame_id = "camera"

        img.height = h
        img.width = w
        img.encoding = "bgr8"
        img.step = w * 3
        img.data = annotated.tobytes()

        self.img_pub.publish(img)


def main():

    rclpy.init()

    node = YoloDetector()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    node.cap.release()

    cv2.destroyAllWindows()

    node.destroy_node()

    rclpy.shutdown()


if __name__ == "__main__":
    main() 
