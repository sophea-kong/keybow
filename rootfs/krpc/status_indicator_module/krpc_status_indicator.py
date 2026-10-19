#!/usr/bin/env python3
# coding: utf-8

import argparse
import datetime
import json
import os
import re
import math

import rospy
from std_msgs.msg import String, ColorRGBA
from geometry_msgs.msg import Point
from visualization_msgs.msg import Marker
from ib2_msgs.msg import Navigation

try:
    from jsk_rviz_plugins.msg import OverlayText
except Exception:
    OverlayText = None

NAVIGATION_TOPIC = "/sensor_fusion/navigation"
DEBUG_OVERLAY_WIDTH = int(os.environ.get("DEBUG_OVERLAY_WIDTH", "300"))
DEBUG_OVERLAY_HEIGHT = 100
DEBUG_OVERLAY_MARGIN = 10
# RViz's OverlayText "left" is relative to the render viewport, which is narrower
# than the desktop because the Displays/Views panels are docked on the left side.
RVIZ_VIEWPORT_WIDTH = int(os.environ.get("RVIZ_VIEWPORT_WIDTH", "1300"))

debug_pose_info = {
    "position": None,
    "orientation": None,
}

JSON_STATUS = "status"
JSON_AREA_ID = "area_id"
JSON_LOST_ITEM = "lost_item"
JSON_NUM = "num"
JSON_CHECKPOINT_ID = "checkpoint_id"
JSON_SUCCESS = "success"
JSON_CHECKPOINT_PASSED = "checkpoint_passed"
JSON_PASSED_BAND = "passed_band"
JSON_SELECTED_BAND = "selected_band"

def _rotate_vector_by_quaternion(vector, quaternion):
    """Rotate vector by quaternion: v' = q * v * q_conjugate"""
    qx, qy, qz, qw = quaternion
    vx, vy, vz = vector

    # Normalize quaternion
    norm_sq = qx*qx + qy*qy + qz*qz + qw*qw
    if norm_sq < 1e-10:
        return [float(vx), float(vy), float(vz)]

    # Quaternion multiplication: q * v * q_conjugate
    # v as quaternion: (vx, vy, vz, 0)
    # q_conjugate: (-qx, -qy, -qz, qw)

    # First: q * v
    t0 = qw*vx + qy*vz - qz*vy
    t1 = qw*vy - qx*vz + qz*vx
    t2 = qw*vz + qx*vy - qy*vx
    t3 = -qx*vx - qy*vy - qz*vz

    # Then: (q*v) * q_conjugate
    return [
        t0*qw + t3*(-qx) - t1*qz + t2*qy,
        t1*qw + t3*(-qy) + t0*qz - t2*qx,
        t2*qw + t3*(-qz) - t0*qy + t1*qx,
    ]

JUDGE_CHECKPOINT_RESULT_TOPIC = "/krpc/judge/checkpoint_result"
JUDGE_GOAL_RESULT_TOPIC = "/krpc/judge/goal_result"

CHECKPOINT_COUNT = 12
GOAL_CHECKPOINT_ID = 12

MISSION_START = "Mission Start"
MISSION_FINISH = "Mission Finish"
CHECKPOINT_PASSED = "CheckPointPassed"
GOALPOINT_PASSED = "GoalPointPassed"
ROUNDING_COMPLETE_ALIAS = "rounding is complete"

DEFAULT_CHEAT_SHEET_PATH = "/tmp/share/logs/latest/cheat_sheet.json"
DEFAULT_MARKER_AREA_CONFIG_PATH = "/krpc/random_env_generator/files/input/area_config.json"
TIME_LIMIT = rospy.Time(300)

YET_DONE = "yet..."
DONE = "Done!"
NOT_APPLICABLE = "N/A"

# Constants for DS coordinate conversion (same values as modify_model_patch.py)
# Define the DS coordinate origin from the Dock's absolute Gazebo coordinates
DS_ORIGIN_X = 10.9358938
DS_ORIGIN_Y = -3.4765598
DS_ORIGIN_Z = 5.6432212

# Same values as DEFAULT_SAFE_AREA in generate_objects.py
DEFAULT_SAFE_AREA = {
    "min": [0.20, -0.80, 0.00],
    "max": [7.00, 0.85, 1.68],
}
SAFE_AREA_MARKER_NS = "safe_area"
SAFE_AREA_COLOR = (1.0, 0.85, 0.1)
SAFE_AREA_LINE_WIDTH = 0.02

checkpoint_info = {
    "passed": [False] * CHECKPOINT_COUNT,
    "active": [True] * CHECKPOINT_COUNT,
    "judged": [False] * CHECKPOINT_COUNT,
    "last_checkpoint": "-",
    "passed_band": {},
}

status_info = {
    "start_flg": False,
    "completed": False,
    "time_start": rospy.Time(0),
    "completed_time": rospy.Time(0),
    "current_status": "Waiting for event",
    "goal_passed": False,
    "level": "-",
}

DEFAULT_MARKER_RADIUS = 0.6
DEFAULT_MARKER_RADII = [0.2, 0.4, 0.6]

COLOR_LARGEST = (0.4, 0.9, 1.0)
COLOR_MIDDLE = (0.0, 1.0, 0.2)
COLOR_SMALLEST = (1.0, 0.1, 0.1)
COLOR_PASSED = (0.6, 1.0, 0.2)


class Score:
    def __init__(self, cheat_sheet_path: str):
        if not os.path.exists(cheat_sheet_path):
            rospy.logwarn("cheat_sheet not found: %s", cheat_sheet_path)
            return

        cheat_sheet = self.load_json(cheat_sheet_path)
        status_info["level"] = str(cheat_sheet.get("Level", "-"))
        self.apply_active_checkpoints(cheat_sheet.get("Checkpoints", []))
        rospy.loginfo(
            "scoreboard mode: %d/%d checkpoints active (level=%s)",
            sum(1 for active in checkpoint_info["active"] if active),
            CHECKPOINT_COUNT,
            status_info["level"],
        )

    @staticmethod
    def apply_active_checkpoints(checkpoints) -> None:
        """Treat only the checkpoints selected by difficulty level as active."""
        if not isinstance(checkpoints, list):
            return

        active_ids = set()
        for cp in checkpoints:
            if not isinstance(cp, dict):
                continue
            checkpoint_id = parse_checkpoint_id(cp.get("checkpointid"))
            if isinstance(checkpoint_id, int) and 1 <= checkpoint_id <= CHECKPOINT_COUNT:
                active_ids.add(checkpoint_id)

        if not active_ids:
            return

        for idx in range(1, CHECKPOINT_COUNT + 1):
            checkpoint_info["active"][idx - 1] = idx in active_ids

    @staticmethod
    def load_json(path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def scoreboard_text() -> str:
        active_count = sum(1 for active in checkpoint_info["active"] if active)
        passed_count = sum(
            1
            for passed, active in zip(checkpoint_info["passed"], checkpoint_info["active"])
            if passed and active
        )
        rows = ""
        for idx in range(1, CHECKPOINT_COUNT + 1):
            if not checkpoint_info["active"][idx - 1]:
                status = NOT_APPLICABLE
            elif checkpoint_info["passed"][idx - 1]:
                band = checkpoint_info["passed_band"].get(idx)
                status = "Lv{}".format(band) if isinstance(band, int) else "OK"
            elif checkpoint_info["judged"][idx - 1]:
                status = "NG"
            else:
                status = "-"
            label = "CP{}(GOAL)".format(idx) if idx == GOAL_CHECKPOINT_ID else "CP{}".format(idx)
            rows += "<tr><td width=\"120\">{}</td><td width=\"80\">{}</td></tr>".format(label, status)

        return (
            "<table><tbody>"
            "<tr><td width=\"200\">Checkpoint Passed</td><td width=\"120\">{}/{}</td></tr>"
            "<tr><td width=\"200\">Last Checkpoint</td><td width=\"120\">{}</td></tr>"
            "<tr><td width=\"200\">GoalPoint</td><td width=\"120\">{}</td></tr>"
            "</tbody></table>"
            "<table><tbody>{}</tbody></table>".format(
                passed_count,
                active_count,
                checkpoint_info["last_checkpoint"],
                DONE if status_info["goal_passed"] else YET_DONE,
                rows,
            )
        )

    @staticmethod
    def detail_text() -> str:
        return "<table><tbody><tr><td>Mission Time Left {}</td></tr></tbody></table>".format(
            Score.mission_time_text()
        )

    @staticmethod
    def mission_time_text() -> str:
        time_left = rospy.Time(0)

        if status_info["start_flg"] and not status_info["completed"]:
            duration = rospy.Time.now() - status_info["time_start"]
            if duration.to_sec() > TIME_LIMIT.to_sec():
                duration = TIME_LIMIT
            time_left = TIME_LIMIT - duration
        elif status_info["completed"]:
            duration = status_info["completed_time"] - status_info["time_start"]
            if duration.to_sec() > TIME_LIMIT.to_sec():
                duration = TIME_LIMIT
            time_left = TIME_LIMIT - duration

        literal = datetime.datetime.fromtimestamp(time_left.to_sec()).strftime("%M:%S.%f")[:-3]
        return "<table><tbody><tr><td>{}</td></tr></tbody></table>".format(literal)


def parse_checkpoint_id(raw_checkpoint_id):
    if isinstance(raw_checkpoint_id, int):
        return raw_checkpoint_id
    if isinstance(raw_checkpoint_id, str):
        m = re.search(r"(\d+)", raw_checkpoint_id)
        if m:
            return int(m.group(1))
    return None


def max_band_radius(score_bands):
    if not isinstance(score_bands, list):
        return None

    radii = []
    for band in score_bands:
        if isinstance(band, dict):
            radius = band.get("radius")
            if isinstance(radius, (int, float)):
                radii.append(float(radius))
    if not radii:
        return None
    return max(radii)


def band_radii_from_band_objects(score_bands):
    if not isinstance(score_bands, list):
        return []

    radii = []
    for band in score_bands:
        if isinstance(band, dict):
            radius = band.get("radius")
            if isinstance(radius, (int, float)):
                radii.append(float(radius))

    if not radii:
        return []
    return sorted(radii)


def default_band_color(band_index, band_count):
    # Expected order: 1=smallest, 2=middle, 3=largest
    if band_count >= 3:
        if band_index == 1:
            return COLOR_SMALLEST
        if band_index == band_count:
            return COLOR_LARGEST
        return COLOR_MIDDLE

    # Fallback for non-3-band definitions
    if band_index == 1:
        return COLOR_SMALLEST
    if band_index == band_count:
        return COLOR_LARGEST
    return COLOR_MIDDLE


def load_checkpoint_markers(cheat_sheet_path):
    if not os.path.exists(cheat_sheet_path):
        rospy.logwarn("cheat_sheet not found for markers: %s", cheat_sheet_path)
        return [], DEFAULT_MARKER_RADIUS

    try:
        with open(cheat_sheet_path, "r", encoding="utf-8") as f:
            cheat_sheet = json.load(f)
    except Exception as e:
        rospy.logwarn("failed to load cheat_sheet for markers (%s): %s", cheat_sheet_path, e)
        return [], DEFAULT_MARKER_RADIUS

    checkpoints = cheat_sheet.get("Checkpoints", [])
    global_band_radii = band_radii_from_band_objects(cheat_sheet.get("checkpoint_score_bands"))
    global_max_radius = max(global_band_radii) if global_band_radii else None

    markers = []
    for cp in checkpoints:
        checkpoint_id = parse_checkpoint_id(cp.get("checkpointid"))
        position_world = cp.get("position")
        marker_pose = cp.get("marker_pose", {})

        if checkpoint_id is None or not isinstance(position_world, list) or len(position_world) != 3:
            continue
        if not all(isinstance(v, (int, float)) for v in position_world):
            continue

        band_radii = band_radii_from_band_objects(cp.get("score_bands"))
        if not band_radii:
            band_radii = list(global_band_radii)
        if not band_radii:
            band_radii = list(DEFAULT_MARKER_RADII)

        markers.append({
            "id": int(checkpoint_id),
            "position": [float(position_world[0]), float(position_world[1]), float(position_world[2])],
            "band_radii": band_radii,
        })

    markers.sort(key=lambda x: x["id"])
    if not markers:
        rospy.logwarn("no valid checkpoints found in cheat_sheet: %s", cheat_sheet_path)

    resolved_global_radius = global_max_radius if global_max_radius is not None else DEFAULT_MARKER_RADIUS
    return markers, float(resolved_global_radius)


def normalize_status(status: str) -> str:
    if status == ROUNDING_COMPLETE_ALIAS:
        return GOALPOINT_PASSED
    return status


def update_area_info(area_id, num):
    checkpoint_id = None

    if isinstance(num, int):
        checkpoint_id = num
    elif isinstance(area_id, int):
        checkpoint_id = area_id

    if checkpoint_id is None:
        return

    if 1 <= checkpoint_id <= CHECKPOINT_COUNT:
        checkpoint_info["passed"][checkpoint_id - 1] = True
        checkpoint_info["judged"][checkpoint_id - 1] = True
        checkpoint_info["last_checkpoint"] = "CP{}".format(checkpoint_id)
    else:
        rospy.logwarn("illegal checkpoint id: %s", checkpoint_id)


def apply_checkpoint_passed_map(passed_map):
    if not isinstance(passed_map, dict):
        return

    for idx in range(1, CHECKPOINT_COUNT + 1):
        key = str(idx)
        if key in passed_map:
            checkpoint_info["passed"][idx - 1] = bool(passed_map[key])
            if checkpoint_info["passed"][idx - 1]:
                checkpoint_info["judged"][idx - 1] = True


def parse_positive_int(value):
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        m = re.search(r"(\d+)", value)
        if m:
            parsed = int(m.group(1))
            return parsed if parsed > 0 else None
    return None


def make_overlay_status(text: str):
    overlay = OverlayText()
    overlay.top = 10
    overlay.left = 10
    overlay.width = 300
    overlay.height = 60
    overlay.text_size = 14
    overlay.line_width = 2
    overlay.font = "DejaVu Sans Mono"
    overlay.text = "[STATUS]\n{}".format(text)
    overlay.fg_color = ColorRGBA(0.302, 1.0, 0.0, 1.0)
    overlay.bg_color = ColorRGBA(0.0, 0.0, 0.0, 0.2)
    return overlay


def make_overlay_debug_position():
    position = debug_pose_info["position"]
    if position is None:
        text = "self position: N/A"
    else:
        text = "X: {:8.3f}\nY: {:8.3f}\nZ: {:8.3f}".format(*position)

    overlay = OverlayText()
    overlay.top = 10
    overlay.left = RVIZ_VIEWPORT_WIDTH - DEBUG_OVERLAY_WIDTH - DEBUG_OVERLAY_MARGIN
    overlay.width = DEBUG_OVERLAY_WIDTH
    overlay.height = DEBUG_OVERLAY_HEIGHT
    overlay.text_size = 14
    overlay.line_width = 2
    overlay.font = "DejaVu Sans Mono"
    overlay.text = "[DEBUG]&nbsp;self&nbsp;position\n{}".format(text)
    overlay.fg_color = ColorRGBA(1.0, 0.8, 0.1, 1.0)
    overlay.bg_color = ColorRGBA(0.0, 0.0, 0.0, 0.4)
    return overlay


def make_scoreboard(check_point, detail_text):
    overlay = OverlayText()
    overlay.top = 80
    overlay.left = 10
    overlay.width = 300
    overlay.height = 460
    overlay.text_size = 12
    overlay.line_width = 2
    overlay.font = "DejaVu Sans Mono"
    overlay.fg_color = ColorRGBA(0.302, 1.0, 0.0, 1.0)
    overlay.bg_color = ColorRGBA(0.0, 0.0, 0.0, 0.2)
    overlay.text = "[CHECK&nbsp;POINT]{}\n{}".format(check_point, detail_text)
    return overlay


def make_marker_topic(checkpoint_marker, band_index, visible, passed_highlight=False):
    marker = Marker()
    marker.header.frame_id = "iss_body"
    marker.header.stamp = rospy.Time.now()
    marker.ns = "checkpoint_sphere"
    marker.id = checkpoint_marker["id"] * 100 + band_index
    marker.action = Marker.DELETE

    if visible:
        marker.action = Marker.ADD
        checkpoint_ds_pos = checkpoint_marker["position"]

        # Convert DS coordinates to Gazebo coordinates
        # DS axis definition: DS.x = -Gazebo_rel.y, DS.y = -Gazebo_rel.x, DS.z = -Gazebo_rel.z
        # Inverse transform: Gazebo.x = DS_ORIGIN.x - DS.y, Gazebo.y = DS_ORIGIN.y - DS.x, Gazebo.z = DS_ORIGIN.z - DS.z
        gazebo_pos = [
            DS_ORIGIN_X - checkpoint_ds_pos[1],
            DS_ORIGIN_Y - checkpoint_ds_pos[0],
            DS_ORIGIN_Z - checkpoint_ds_pos[2],
        ]

        marker.pose.position.x = gazebo_pos[0]
        marker.pose.position.y = gazebo_pos[1]
        marker.pose.position.z = gazebo_pos[2]
        marker.pose.orientation.w = 1.0

        radius = checkpoint_marker["band_radii"][band_index - 1]
        diameter = radius * 2.0
        marker.scale.x = diameter
        marker.scale.y = diameter
        marker.scale.z = diameter

        if passed_highlight:
            marker.color.r = COLOR_PASSED[0]
            marker.color.g = COLOR_PASSED[1]
            marker.color.b = COLOR_PASSED[2]
        else:
            color = default_band_color(band_index, len(checkpoint_marker["band_radii"]))
            marker.color.r = color[0]
            marker.color.g = color[1]
            marker.color.b = color[2]
        marker.color.a = 0.3
        marker.type = Marker.SPHERE

    return marker


def ds_to_gazebo(ds_position):
    """Convert DS coordinates to Gazebo coordinates.

    DS axis definition: DS.x = -Gazebo_rel.y, DS.y = -Gazebo_rel.x, DS.z = -Gazebo_rel.z
    """
    return [
        DS_ORIGIN_X - float(ds_position[1]),
        DS_ORIGIN_Y - float(ds_position[0]),
        DS_ORIGIN_Z - float(ds_position[2]),
    ]


def load_safe_area(area_config_path):
    if not os.path.exists(area_config_path):
        rospy.logwarn("area_config not found for safe area: %s", area_config_path)
        return DEFAULT_SAFE_AREA

    try:
        with open(area_config_path, "r", encoding="utf-8") as f:
            area_config = json.load(f)
    except Exception as e:
        rospy.logwarn("failed to load area_config (%s): %s", area_config_path, e)
        return DEFAULT_SAFE_AREA

    if "SafeArea" not in area_config:
        return DEFAULT_SAFE_AREA

    safe_area = area_config.get("SafeArea")
    if not isinstance(safe_area, dict):
        return None

    lower = safe_area.get("min")
    upper = safe_area.get("max")
    if not isinstance(lower, list) or not isinstance(upper, list):
        return None
    if len(lower) < 3 or len(upper) < 3:
        return None

    return {
        "min": [float(lower[i]) for i in range(3)],
        "max": [float(upper[i]) for i in range(3)],
    }


def make_safe_area_marker(safe_area):
    marker = Marker()
    marker.header.frame_id = "iss_body"
    marker.header.stamp = rospy.Time.now()
    marker.ns = SAFE_AREA_MARKER_NS
    marker.id = 0
    marker.type = Marker.LINE_LIST
    marker.action = Marker.ADD
    marker.pose.orientation.w = 1.0
    marker.scale.x = SAFE_AREA_LINE_WIDTH
    marker.color.r = SAFE_AREA_COLOR[0]
    marker.color.g = SAFE_AREA_COLOR[1]
    marker.color.b = SAFE_AREA_COLOR[2]
    marker.color.a = 0.8

    lower = safe_area["min"]
    upper = safe_area["max"]
    corners = []
    for xi in (lower[0], upper[0]):
        for yi in (lower[1], upper[1]):
            for zi in (lower[2], upper[2]):
                gazebo = ds_to_gazebo([xi, yi, zi])
                corners.append(Point(x=gazebo[0], y=gazebo[1], z=gazebo[2]))

    # corners index = (x<<2) | (y<<1) | z
    edges = [
        (0, 1), (2, 3), (4, 5), (6, 7),
        (0, 2), (1, 3), (4, 6), (5, 7),
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]
    for a, b in edges:
        marker.points.append(corners[a])
        marker.points.append(corners[b])

    return marker


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cheat_sheet_path", default=DEFAULT_CHEAT_SHEET_PATH)
    parser.add_argument("-a", "--area_config_path", default=DEFAULT_MARKER_AREA_CONFIG_PATH)
    parser.add_argument("--debug", action="store_true", help="show self position overlay for debugging")
    return parser.parse_args()


def main():
    rospy.init_node("krpc_status_indicator")

    if OverlayText is None:
        rospy.logerr("jsk_rviz_plugins.msg.OverlayText is unavailable; exit status indicator.")
        return

    args = parse_args()
    score = Score(args.cheat_sheet_path)
    checkpoint_markers, marker_radius = load_checkpoint_markers(args.cheat_sheet_path)
    safe_area = load_safe_area(args.area_config_path)
    if safe_area is None:
        rospy.loginfo("safe area marker is disabled")
    else:
        rospy.loginfo("safe area marker: min=%s max=%s", safe_area["min"], safe_area["max"])
    rospy.loginfo(
        "checkpoint marker mode: %d spheres loaded from %s (max score_band radius=%.3f)",
        len(checkpoint_markers),
        args.cheat_sheet_path,
        marker_radius,
    )

    status_pub = rospy.Publisher("krpc/comm/indicator", OverlayText, queue_size=1, latch=True)
    board_pub = rospy.Publisher("krpc/comm/scoreBoard", OverlayText, queue_size=1, latch=True)
    marker_pub = rospy.Publisher("krpc/comm/marker", Marker, queue_size=10, latch=True)

    debug_pub = None
    if args.debug:
        debug_pub = rospy.Publisher("krpc/comm/debug_position", OverlayText, queue_size=1, latch=True)

        def navigation_callback(data):
            pose = data.pose.pose
            debug_pose_info["position"] = (pose.position.x, pose.position.y, pose.position.z)
            debug_pose_info["orientation"] = (
                pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w,
            )

        rospy.Subscriber(NAVIGATION_TOPIC, Navigation, navigation_callback, queue_size=1)
        rospy.loginfo("debug mode enabled: self position overlay subscribed to %s", NAVIGATION_TOPIC)

    def gsdata_callback(data):
        try:
            request = json.loads(data.data)
        except Exception as e:
            rospy.logwarn_throttle(5, "invalid /gs/data payload: %s", e)
            return

        status = normalize_status(request.get(JSON_STATUS, None))
        if status == MISSION_START:
            status_info["start_flg"] = True
            status_info["time_start"] = rospy.Time.now()
        elif status == CHECKPOINT_PASSED:
            pass
        elif status == GOALPOINT_PASSED:
            pass
        elif status == MISSION_FINISH:
            status_info["completed"] = True
            status_info["completed_time"] = rospy.Time.now()

        if status is not None:
            status_info["current_status"] = status
            status_pub.publish(make_overlay_status(status_info["current_status"]))

        area_id = request.get(JSON_AREA_ID, None)
        num_of_item = request.get(JSON_NUM, None)
        if area_id is not None or num_of_item is not None:
            update_area_info(area_id, num_of_item)

    def checkpoint_result_callback(data):
        try:
            result = json.loads(data.data)
        except Exception as e:
            rospy.logwarn_throttle(5, "invalid checkpoint result payload: %s", e)
            return

        status = result.get(JSON_STATUS)
        if status != CHECKPOINT_PASSED:
            return

        apply_checkpoint_passed_map(result.get(JSON_CHECKPOINT_PASSED))

        checkpoint_id = parse_checkpoint_id(result.get(JSON_CHECKPOINT_ID))
        success = bool(result.get(JSON_SUCCESS, False))
        passed_band = parse_positive_int(result.get(JSON_SELECTED_BAND))
        if passed_band is None:
            passed_band = parse_positive_int(result.get(JSON_PASSED_BAND))

        if isinstance(checkpoint_id, int) and 1 <= checkpoint_id <= CHECKPOINT_COUNT:
            checkpoint_info["passed"][checkpoint_id - 1] = success
            checkpoint_info["judged"][checkpoint_id - 1] = True
            if success:
                checkpoint_info["last_checkpoint"] = "CP{}".format(checkpoint_id)
                checkpoint_info["passed_band"][checkpoint_id] = passed_band
            elif checkpoint_id in checkpoint_info["passed_band"]:
                del checkpoint_info["passed_band"][checkpoint_id]

        status_info["current_status"] = (
            "{} CP{} {}".format(
                CHECKPOINT_PASSED,
                checkpoint_id if checkpoint_id is not None else "?",
                "OK" if success else "NG",
            )
        )

    def goal_result_callback(data):
        try:
            result = json.loads(data.data)
        except Exception as e:
            rospy.logwarn_throttle(5, "invalid goal result payload: %s", e)
            return

        status = result.get(JSON_STATUS)
        if status != GOALPOINT_PASSED:
            return

        success = bool(result.get(JSON_SUCCESS, False))
        status_info["goal_passed"] = success
        status_info["current_status"] = "{} {}".format(
            GOALPOINT_PASSED,
            "OK" if success else "NG",
        )

    rospy.Subscriber("/gs/data", String, gsdata_callback, queue_size=20)
    rospy.Subscriber(JUDGE_CHECKPOINT_RESULT_TOPIC, String, checkpoint_result_callback, queue_size=20)
    rospy.Subscriber(JUDGE_GOAL_RESULT_TOPIC, String, goal_result_callback, queue_size=20)

    rate = rospy.Rate(10)
    while not rospy.is_shutdown():
        status_pub.publish(make_overlay_status(status_info["current_status"]))
        board_pub.publish(
            make_scoreboard(score.scoreboard_text(), score.detail_text())
        )
        if debug_pub is not None:
            debug_pub.publish(make_overlay_debug_position())
        if safe_area is not None:
            marker_pub.publish(make_safe_area_marker(safe_area))
        for checkpoint_marker in checkpoint_markers:
            checkpoint_id = checkpoint_marker["id"]
            band_count = len(checkpoint_marker["band_radii"])
            if band_count <= 0:
                continue

            passed = False
            if 1 <= checkpoint_id <= CHECKPOINT_COUNT:
                passed = checkpoint_info["passed"][checkpoint_id - 1]

            passed_band = checkpoint_info["passed_band"].get(checkpoint_id)
            if passed and isinstance(passed_band, int) and 1 <= passed_band <= band_count:
                for band_index in range(1, band_count + 1):
                    marker_pub.publish(
                        make_marker_topic(
                            checkpoint_marker,
                            band_index,
                            visible=(band_index == band_count),
                            passed_highlight=(band_index == band_count),
                        )
                    )
            else:
                for band_index in range(1, band_count + 1):
                    marker_pub.publish(make_marker_topic(checkpoint_marker, band_index, visible=True))
        rate.sleep()


if __name__ == "__main__":
    main()
