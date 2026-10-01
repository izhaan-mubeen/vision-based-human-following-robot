import math
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
from geometry_msgs.msg import Twist
from turtlesim.msg import Pose


class Follower(Node):
    def __init__(self):
        super().__init__("follower")

        self.declare_parameter("kp", 5.0)
        self.declare_parameter("timeout", 0.5)

        self.theta = 0.0
        self.theta_des = math.pi / 2

        self.last_det = self.get_clock().now()

        self.locked_id = None
        self.x_s = 0.0

        self.create_subscription(
            Float32MultiArray,
            "/detections",
            self.on_det,
            10
        )

        self.create_subscription(
            Pose,
            "/turtle1/pose",
            self.on_pose,
            10
        )

        self.pub = self.create_publisher(
            Twist,
            "/turtle1/cmd_vel",
            10
        )

        self.create_timer(
            0.05,
            self.control_loop
        )


    def on_pose(self, msg):
        self.theta = msg.theta


    def on_det(self, msg):

        d = list(msg.data)

        # Agar width/height bhi nahi aaye
        if len(d) < 2:
            return

        w = d[0]

        objs = []

        # Har detection = 6 numbers
        # cx, cy, width, height, confidence, class_id
        for i in range(2, len(d), 6):

            obj = d[i:i+6]

            # incomplete detection ignore
            if len(obj) == 6:
                objs.append(obj)


        # Koi person detect nahi hua
        if not objs:
            self.locked_id = None
            return


        ids = [o[5] for o in objs]


        # Naya target choose karo
        if self.locked_id not in ids:

            self.locked_id = max(
                objs,
                key=lambda o: o[2] * o[3]
            )[5]


        target = objs[ids.index(self.locked_id)]


        # Camera center error
        x_norm = (target[0] - w / 2) / (w / 2)


        # Smooth movement
        self.x_s = (
            0.3 * x_norm +
            0.7 * self.x_s
        )


        # Desired turtle angle
        self.theta_des = (
            math.pi / 2 -
            self.x_s * math.pi / 2
        )


        self.last_det = self.get_clock().now()



    def control_loop(self):

        age = (
            self.get_clock().now() -
            self.last_det
        ).nanoseconds * 1e-9


        cmd = Twist()


        # Detection fresh hai
        if age < self.get_parameter("timeout").value:

            diff = self.theta_des - self.theta

            # angle wrap -pi to pi
            err = math.atan2(
                math.sin(diff),
                math.cos(diff)
            )


            kp = self.get_parameter("kp").value


            cmd.angular.z = max(
                -3.0,
                min(3.0, kp * err)
            )


        else:
            # Agar person lost ho jaye to stop
            cmd.angular.z = 0.0


        self.pub.publish(cmd)



def main():

    rclpy.init()

    node = Follower()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass


    node.destroy_node()

    rclpy.shutdown()



if __name__ == "__main__":
    main()
