#!/usr/bin/env python3
# coding: utf-8

from datetime import datetime
import argparse
import json
import os

import numpy as np
import rospy
from ib2_msgs.msg import Navigation
from std_msgs.msg import String

JSON_STATUS = "status"
JSON_UNDOCK_START = "Undocking..."
JSON_STATUS_START = "Mission Start"
JSON_STATUS_QR = "Discovered QR"
JSON_SNAPSHOT_START = "Taking snapshots start"
JSON_SNAPSHOT_FINISH = "Taking snapshots finish"
JSON_ROUNDING_COMPLETE = "rounding is complete"
JSON_STATUS_CP = "CheckPointPassed"
JSON_STATUS_GOAL = "GoalPointPassed"
JSON_STATUS_FINISH = "Mission Finish"

DEFAULT_RESULT_PATH = "/tmp/share/logs/latest/data.json"
DEFAULT_IB2_LOG_PATH = os.path.join(os.environ.get("HOME", "/tmp"), "ib2.log")

# (x, y, z) -> (x, -z, y)
ROTATION_MATRIX = np.array(
    [[1.0, 0.0, 0.0],
     [0.0, 0.0, -1.0],
     [0.0, 1.0, 0.0]],
    dtype=float,
)


def normalize_status(status: str) -> str:
    if status == JSON_ROUNDING_COMPLETE:
        return JSON_STATUS_GOAL
    return status


def quaternion_multiply(q1, q2):
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return [
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
    ]


class Recorder:
    def __init__(self, result_path: str, ib2_log_path: str):
        self.current_secs = -1
        self.result_path = result_path
        self.ib2_log_path = ib2_log_path

        self.data = {
            "result": {
                "resultID": "",
                "teamName": "",
                "resultDate": "",
                "roundType": "",
                "totalTime": 0,
                "totalTimeScore": 0,
                "totalCheckPointScore": 0,
                "totalScore": 0,
                "passORfail": "Pass",
            },
            "stage": {
                "targetRelativeCoordinates": [0, 0, 0],
                "kozType": 1,
            },
            "scene": [],
            "moveData": [],
        }

        os.makedirs(os.path.dirname(self.result_path), exist_ok=True)
        rospy.on_shutdown(self.shutdown_hook)
        rospy.loginfo("[KRPC_FLIGHT_RECORDER] Start recording")

    def gsdata_callback(self, data):
        try:
            request = json.loads(data.data)
        except Exception as e:
            rospy.logwarn_throttle(5, "[KRPC_FLIGHT_RECORDER] invalid /gs/data payload: %s", e)
            return

        status = normalize_status(request.get(JSON_STATUS, None))
        if status is None:
            return

        if status == JSON_UNDOCK_START:
            self.new_scene("Undocking", self.current_secs)
        elif status == JSON_STATUS_START:
            self.new_scene("MissionStart", self.current_secs)
        elif status == JSON_STATUS_QR:
            self.new_scene("DiscoveredQR", self.current_secs)
        elif status == JSON_SNAPSHOT_START:
            self.new_scene("TakingSnapshots", self.current_secs)
        elif status == JSON_SNAPSHOT_FINISH:
            self.new_scene("GoToGoal", self.current_secs)
        elif status == JSON_STATUS_CP:
            self.new_scene("CheckPointPassed", self.current_secs)
        elif status == JSON_STATUS_GOAL:
            self.new_scene("GoalPointPassed", self.current_secs)
        elif status == JSON_STATUS_FINISH:
            self.new_scene("MissionFinish", self.current_secs)
            self.output_result()
            rospy.loginfo("[KRPC_FLIGHT_RECORDER] Finish recording")
            rospy.signal_shutdown("mission finished")

    def navigation_callback(self, data: Navigation):
        pose_stamped = data.pose
        if pose_stamped is None:
            return

        secs = int(pose_stamped.header.stamp.secs)
        if secs < 0:
            return

        # Record at 1-second intervals.
        if self.current_secs == secs:
            return

        pose = pose_stamped.pose
        self.current_secs = secs
        self.update_ib2_log(pose.position.x, pose.position.y, pose.position.z)

        if len(self.data["scene"]) > 0:
            self.data["moveData"].append(self.make_move_data(secs, pose))

    def new_scene(self, scene_name: str, start_time: int):
        self.data["scene"].append(
            {
                "sceneName": scene_name,
                "startTime": max(0, int(start_time)),
                "sceneScore": None,
                "camImage": None,
            }
        )
        rospy.loginfo("[KRPC_FLIGHT_RECORDER] New scene %s at %s", scene_name, start_time)

    def make_move_data(self, timestamp: int, pose):
        pos = np.array([pose.position.x * 100.0, pose.position.y * 100.0, pose.position.z * 100.0], dtype=float)
        rot_pos = ROTATION_MATRIX.dot(pos).tolist()
        rot_ori = self.rotate_quaternion_viewer_frame(
            [pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w]
        )

        return {
            "timestamp": int(timestamp),
            "position": rot_pos,
            "orientation": rot_ori,
        }

    @staticmethod
    def rotate_quaternion_viewer_frame(q):
        # Rotation for (x, y, z) -> (x, -z, y) equals +90deg around X axis.
        q_rot = [0.7071067811865475, 0.0, 0.0, 0.7071067811865476]
        q_out = quaternion_multiply(q_rot, q)
        return [float(q_out[0]), float(q_out[1]), float(q_out[2]), float(q_out[3])]

    def output_result(self):
        with open(self.result_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False, sort_keys=False, separators=(",", ": "))

    def update_ib2_log(self, x, y, z):
        line = (
            datetime.now().strftime("%Y/%m/%d-%H:%M:%S")
            + " x:" + str(x)
            + " y:" + str(y)
            + " z:" + str(z)
            + "\n"
        )
        with open(self.ib2_log_path, "a", encoding="utf-8") as f:
            f.write(line)

    @staticmethod
    def shutdown_hook():
        rospy.loginfo("[KRPC_FLIGHT_RECORDER] Shutdown node")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", default=DEFAULT_RESULT_PATH, help="Path to output data.json")
    parser.add_argument("-l", "--log", default=DEFAULT_IB2_LOG_PATH, help="Path to IB2 text log")
    return parser.parse_args()


def main():
    args = parse_args()
    rospy.init_node("krpc_flight_recorder")

    if os.path.exists(args.log):
        os.remove(args.log)

    recorder = Recorder(args.output, args.log)

    rospy.Subscriber("/gs/data", String, recorder.gsdata_callback, queue_size=50)
    rospy.Subscriber("/sensor_fusion/navigation", Navigation, recorder.navigation_callback, queue_size=5)

    rospy.spin()


if __name__ == "__main__":
    main()
