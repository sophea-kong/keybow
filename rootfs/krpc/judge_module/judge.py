#! /usr/bin/env python
# coding:UTF-8

import argparse
import rospy
import numpy as np
import math
import json
from geometry_msgs.msg import Pose
from std_msgs.msg import Bool
from std_msgs.msg import String
from ib2_msgs.msg import Navigation
import tf
import datetime
import os
import threading
import requests
import copy

# API server to scoring
SCORE_API_URL = os.getenv("SCORE_API_URL")

# Default values for startup options
DEFAULT_LOG_ROOT_DIR = "/tmp/share/logs"
DEFAULT_CHEATSHEET_PATH = os.path.join(DEFAULT_LOG_ROOT_DIR, "latest", "cheat_sheet.json")
DEFAULT_MARKER_AREA_CONFIG_PATH = "/krpc/random_env_generator/files/input/area_config.json"
DEFAULT_OUTPUT_DIR = "./"
DEFAULT_RESULT_FILE_NAME = "result.json"
DEFAULT_FINISH_FILE_NAME = "finish_report"
DEFAULT_ROW_FILE_NAME = "data.log"

DEFAULT_POSE_PATH = "localization_history.txt"

# Keys for the json string sent from the APK
JSON_STATUS = "status"
JSON_TIMESTAMP = "timestamp"  # for test_game_scenario
JSON_STATUS_START = "Mission Start"
JSON_STATUS_FINISH = "Mission Finish"
JSON_STATUS_CHECKPOINT = "CheckPointPassed"
#UNDOCK_START = "Undock Start"
# JSON_SNAPSHOT_START = "Taking snapshots of Target start"  # not used
#JSON_TAKING_SNAPSHOT = "Taking a snapshot of Target"
#JSON_SNAPSHOT_FINISH = "Taking snapshots of Target finish"  # not used
JSON_TARGET_INFO = "target_info"
JSON_TARGET_ID = "target_id"
JSON_PHASE_NUMBER = "phase_number"
JSON_QR_INFO = "qr_info"
JSON_FAILED = "failed"
JSON_ROUNDING_COMPLETE = "rounding completed"

# Output destination for the file written when the simulator fails to start
FAILED_FILE_NAME = os.environ['HOME'] + "/failed_to_exec_simulation"

# TF frame IDs
TF_FRAME_BASE = "world"
TF_FRAME_VEC0 = "rpc_vec0"      # Main camera position vector
TF_FRAME_VEC1 = "rpc_vec1"      # Main camera direction vector

# MainCam position information
CAM_F_X = 0.14
CAM_F_Y = 0
CAM_F_Z = 0

# Time limit (SEC)
# Resolution for accumulating bonus (SEC)
T_CYCLE = 0.1
DEFAULT_CHECKPOINT_RADII = [0.20, 0.40, 0.60]
DEFAULT_CHECKPOINT_SCORES = [3, 2, 1]

DEFAULT_CHECKPOINT_RESULT_TOPIC = "/krpc/judge/checkpoint_result"
DEFAULT_GOAL_RESULT_TOPIC = "/krpc/judge/goal_result"
JSON_SELECTED_BAND = "selected_band"

# json keys for the cheat sheet (answer) file
class CHEAT_KEY():
  GOAL="Goal"
  CORRECT_QR_CONTENT="correct_qr_content"
  LOST_ITEMS="LostItems"
  AREA_ID="areaId"

# json keys for the area config file
# json keys for the result file
class RESULT_KEY():
  MISSIONTIME="Mission Time"
  TIMESTAMP="timestamp"
  ARRIVAL="arrival"
  DISTANCE="distance"
  REPORT_TRY="try"
  REPORT_SUCCESS="success"

  ROUNDING_REPORT="RoundingReport"
  FOUND_REPORT="FoundReport"
  CAMERA_ANGLE="cameraAngle"
  ILLEGAL="Illegal"
  CALC_N="TimeBonusN"

class Referee():
  def __init__(self, cheatsheet_path, output_dir, result_file, finish_file, row_file, debug):

    self.test_mode = False
    self.debug = debug
    self.sim_mode = os.getenv("SIM_MODE", "regular").strip().lower()
    if self.sim_mode not in ("regular", "beginners"):
      rospy.logwarn("Unknown SIM_MODE=%s. Falling back to regular mode.", self.sim_mode)
      self.sim_mode = "regular"
    rospy.loginfo("Judge SIM_MODE=%s", self.sim_mode)
    self.gameHasStarted = False
    self.finishflag = 0
    self.score_api_final_sent = False
    self.checkpoint_result_publisher = rospy.Publisher(
      DEFAULT_CHECKPOINT_RESULT_TOPIC,
      String,
      queue_size=10,
      latch=True,
    )
    self.goal_result_publisher = rospy.Publisher(
      DEFAULT_GOAL_RESULT_TOPIC,
      String,
      queue_size=10,
      latch=True,
    )

    # for debug
    if self.debug:
      from tool.marker_pub_tool import MarkerPubTool
      self.marker_tool = MarkerPubTool()

    # Variable holding the Int-Ball2 position/orientation
    self.ib2_pose = None

    # Load the answer file
    self.cheatsheet_path = self.resolve_cheatsheet_path(cheatsheet_path)
    self.cheat_data = self.load_json(self.cheatsheet_path)
    self._checkpoint_rules, self._checkpoint_defaults = self.load_checkpoint_rules()
    self._goal_rule = self.load_goal_rule()
    self.judge_state = {
      "mission_started": False,
      "mission_finished": False,
      "mission_start_ros_time": None,
      "mission_finish_ros_time": None,
      "checkpoints": {},
      "goal": None,
      "events": []
    }

    # Result output destination directory path
    self.output_dir = output_dir

    # Scoring result file path
    self.result_path = os.path.join(self.output_dir, result_file)
    self.finish_path = os.path.join(self.output_dir, finish_file)
    # Raw data file path
    self.row_path = os.path.join(self.output_dir, row_file)
    self.row_f = open(self.row_path, "a")
    # pose file path
    self.pose_path = os.path.join(self.output_dir, DEFAULT_POSE_PATH)
    # Close the stream on shutdown
    rospy.on_shutdown(self.shutdown_hook)

    # Scoring result JSON string
    self.result_json = {
                          RESULT_KEY.MISSIONTIME: {},
                          RESULT_KEY.ROUNDING_REPORT: {
                            RESULT_KEY.TIMESTAMP: "",
                            RESULT_KEY.ARRIVAL: {
                              RESULT_KEY.REPORT_TRY: False,
                              RESULT_KEY.REPORT_SUCCESS: False,
                            },
                          },
                          RESULT_KEY.FOUND_REPORT: {
                          },
                          RESULT_KEY.ILLEGAL: False,
                            RESULT_KEY.CALC_N: 0,
                            "JudgeReport": {}
                       }

    # Unit vector used for estimating the approach location
    # The Int-Ball2 direction vector (1,0,0) at attitude (x,y,z) = (0,0,0), with a 4th dimension added for computation
    self.unit_vec = np.array([1, 0, 0, 1])   #(x,y,z,1)

    # Vector for correcting the main camera position
    self.navcam_def = np.array([CAM_F_X, CAM_F_Y, CAM_F_Z, 1])

    # dynamic tf
    self.broadcaster = tf.TransformBroadcaster()
    self.listener = tf.TransformListener()

    self.status = 0

    self.thread = None
    self.stop_thread = threading.Event()
    self.sync_judge_report()

  def resolve_cheatsheet_path(self, cheatsheet_path):
    candidates = []
    if cheatsheet_path:
      candidates.append(cheatsheet_path)

    latest_path = os.path.join(DEFAULT_LOG_ROOT_DIR, "latest", "cheat_sheet.json")
    if latest_path not in candidates:
      candidates.append(latest_path)

    for candidate in candidates:
      if candidate and os.path.exists(candidate):
        rospy.loginfo("Use cheat_sheet path: {}".format(candidate))
        return candidate

    raise IOError("cheat_sheet.json not found in share logs: {}".format(candidates))

  def load_checkpoint_rules(self):
    defaults = {
      "bands": self.normalize_bands(DEFAULT_CHECKPOINT_RADII, DEFAULT_CHECKPOINT_SCORES)
    }
    checkpoint_rules = {}

    for key in ("checkpoint_score_bands", "CheckpointScoreBands", "score_bands", "ScoreBands"):
      bands = self.bands_from_band_objects(self.cheat_data.get(key))
      if bands:
        defaults["bands"] = bands
        break

    checkpoints = self.cheat_data.get("Checkpoints")
    if checkpoints is None:
      checkpoints = self.cheat_data.get("checkpoints")

    if isinstance(checkpoints, list) and checkpoints:
      for idx, item in enumerate(checkpoints, start=1):
        if not isinstance(item, dict):
          continue
        checkpoint_id = item.get("checkpointid", item.get("checkpoint_id", item.get("id", idx)))
        position = item.get("position")
        marker_pose = item.get("marker_pose")
        if not isinstance(marker_pose, dict):
          marker_pose = {
            "position": position,
            "quaternion": item.get("marker_quaternion", [0.0, 0.0, 0.0, 1.0])
          }
        bands = self.extract_item_bands(item)
        attitude = item.get("attitude")
        checkpoint_rules[checkpoint_id] = {
          "position": position,
          "marker_pose": marker_pose,
          "bands": bands if bands else defaults["bands"],
          "attitude": attitude,
        }
    else:
      rospy.logwarn("Checkpoints definition not found in cheat_sheet. LostItems fallback is disabled.")

    return checkpoint_rules, defaults

  def load_goal_rule(self):
    rule = {
      "checkpoint_id": None,
      "all_checkpoints_bonus": 0,
    }
    goal = self.cheat_data.get(CHEAT_KEY.GOAL)
    if isinstance(goal, dict):
      checkpoint_id = goal.get("checkpoint_id")
      if checkpoint_id is not None:
        rule["checkpoint_id"] = int(checkpoint_id)
      bonus = goal.get("all_checkpoints_bonus", goal.get("score", goal.get("point", goal.get("points", 0))))
      rule["all_checkpoints_bonus"] = int(bonus)
    return rule

  def normalize_bands(self, radii, scores):
    bands = []
    if radii is None or scores is None:
      return bands
    for radius, score in zip(radii, scores):
      try:
        bands.append((float(radius), int(score)))
      except Exception:
        continue
    bands.sort(key=lambda x: x[0])
    return bands

  def bands_from_band_objects(self, band_objects, is_attitude=False):
    bands = []
    if not isinstance(band_objects, list):
      return bands
    for band in band_objects:
      if not isinstance(band, dict):
        continue
      if is_attitude:
        threshold = band.get("angle", band.get("margin", band.get("threshold")))
      else:
        threshold = band.get("radius", band.get("margin", band.get("distance")))
      score = band.get("level", band.get("score", band.get("point", band.get("points"))))
      try:
        bands.append((float(threshold), int(score)))
      except Exception:
        continue
    bands.sort(key=lambda x: x[0])
    return bands

  def extract_item_bands(self, item):
    if not isinstance(item, dict):
      return []
    for key in ("score_bands", "scoreBands", "bands"):
      bands = self.bands_from_band_objects(item.get(key))
      if bands:
        return bands

    radii = item.get("margins", item.get("radii", item.get("score_bands")))
    scores = item.get("scores", item.get("points", item.get("score_values")))
    return self.normalize_bands(radii, scores)

  def classify_distance_to_band(self, distance, bands):
    for idx, (radius, level) in enumerate(bands, start=1):
      if distance <= float(radius):
        return level
    return 0

  def classify_attitude_to_band(self, angle_deg, attitude_bands):
    for idx, (angle_threshold, level) in enumerate(attitude_bands, start=1):
      if angle_deg <= float(angle_threshold):
        return level
    return 0

  def distance_3d(self, p1, p2):
    dx = float(p1[0]) - float(p2[0])
    dy = float(p1[1]) - float(p2[1])
    dz = float(p1[2]) - float(p2[2])
    return math.sqrt(dx * dx + dy * dy + dz * dz)

  def _rotate_vector_by_quaternion(self, vector, quaternion):
    """Rotate vector by quaternion: v' = q * v * q_conjugate"""
    qx, qy, qz, qw = self.normalize_quaternion(quaternion)
    vx, vy, vz = vector

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

  def normalize_quaternion(self, quaternion):
    if quaternion is None:
      return [0.0, 0.0, 0.0, 1.0]
    if isinstance(quaternion, dict):
      qx = float(quaternion.get("x", 0.0))
      qy = float(quaternion.get("y", 0.0))
      qz = float(quaternion.get("z", 0.0))
      qw = float(quaternion.get("w", 1.0))
    else:
      qx = float(quaternion[0])
      qy = float(quaternion[1])
      qz = float(quaternion[2])
      qw = float(quaternion[3])

    norm = math.sqrt(qx*qx + qy*qy + qz*qz + qw*qw)
    if norm <= 0.0:
      return [0.0, 0.0, 0.0, 1.0]
    return [qx / norm, qy / norm, qz / norm, qw / norm]

  def _quaternion_angle_diff(self, q_current, q_target):
    qc = self.normalize_quaternion(q_current)
    qt = self.normalize_quaternion(q_target)
    dot = qc[0] * qt[0] + qc[1] * qt[1] + qc[2] * qt[2] + qc[3] * qt[3]
    # q and -q represent the same orientation.
    dot = abs(max(-1.0, min(1.0, float(dot))))
    return math.degrees(2.0 * math.acos(dot))

  def _normalize_vector(self, vector):
    x, y, z = float(vector[0]), float(vector[1]), float(vector[2])
    norm = math.sqrt(x * x + y * y + z * z)
    if norm <= 1e-9:
      return [0.0, 0.0, 0.0]
    return [x / norm, y / norm, z / norm]

  def _vector_angle_deg(self, v1, v2):
    dot = v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.acos(dot))

  def _twist_angle_deg(self, quaternion, axis):
    # Return the twist angle (roll component) around the given axis, with sign.
    qx, qy, qz, qw = self.normalize_quaternion(quaternion)
    if qw < 0.0:
      qx, qy, qz, qw = -qx, -qy, -qz, -qw
    dot = qx * axis[0] + qy * axis[1] + qz * axis[2]
    return math.degrees(2.0 * math.atan2(dot, qw))

  def _wrap_angle_deg(self, angle_deg):
    return (angle_deg + 180.0) % 360.0 - 180.0

  def _evaluate_centering_and_roll(self, ib2_position, ib2_quaternion, marker_position, target_quaternion):
    # centering: \u5b9f\u969b\u306e\u30ab\u30e1\u30e9\u8996\u7dda\u65b9\u5411 vs \u5b9f\u969b\u306e\u30de\u30fc\u30ab\u30fc\u65b9\u5411\u306e\u306a\u3059\u89d2\u3002\u7406\u60f3\u59ff\u52e2\u306f\u4f7f\u308f\u306a\u3044\u3002
    view_axis = self._normalize_vector([
      float(marker_position[i]) - float(ib2_position[i]) for i in range(3)
    ])
    camera_forward = self._normalize_vector(
      self._rotate_vector_by_quaternion([1.0, 0.0, 0.0], ib2_quaternion)
    )
    centering_angle_deg = self._vector_angle_deg(camera_forward, view_axis)

    # roll: \u8996\u7dda\u8ef8(view_axis)\u307e\u308f\u308a\u306e\u30cd\u30b8\u308c\u3092\u5b9f\u59ff\u52e2\u30fb\u76ee\u6a19\u59ff\u52e2\u3067\u305d\u308c\u305e\u308c\u6c42\u3081\u3066\u5dee\u3092\u3068\u308b\u3002
    roll_actual_deg = self._twist_angle_deg(ib2_quaternion, view_axis)
    roll_target_deg = self._twist_angle_deg(target_quaternion, view_axis)
    roll_diff_deg = abs(self._wrap_angle_deg(roll_actual_deg - roll_target_deg))

    return centering_angle_deg, roll_diff_deg

  def ros_time_string(self, ros_time_sec=None):
    if ros_time_sec is None:
      ros_time_sec = rospy.Time.now().to_sec()
    return datetime.datetime.fromtimestamp(ros_time_sec).strftime("%Y%m%d %H%M%S%f")[:-3]

  def current_pose_snapshot(self):
    if self.ib2_pose is None:
      return None
    return {
      "position": [
        float(self.ib2_pose.position.x),
        float(self.ib2_pose.position.y),
        float(self.ib2_pose.position.z),
      ],
      "quaternion": [
        float(self.ib2_pose.orientation.x),
        float(self.ib2_pose.orientation.y),
        float(self.ib2_pose.orientation.z),
        float(self.ib2_pose.orientation.w),
      ]
    }

  def evaluate_checkpoint_navigation(self, checkpoint_id):
    rule = self.get_checkpoint_rule(checkpoint_id)
    if rule is None:
      return False, "unknown checkpoint", None

    pose = self.current_pose_snapshot()
    if pose is None:
      return False, "navigation pose unavailable", None

    # Checkpoint position is in world coordinates.
    target_position = rule.get("position")
    marker_pose = rule.get("marker_pose", {})
    marker_position = marker_pose.get("position", [0, 0, 0])

    bands = rule.get("bands") or self._checkpoint_defaults.get("bands", [])
    if not isinstance(target_position, list) or len(target_position) < 3:
      return False, "invalid checkpoint position", None
    if not isinstance(marker_position, list) or len(marker_position) < 3:
      return False, "invalid marker position", None
    if not bands:
      return False, "invalid checkpoint bands", None

    nav_pos = pose["position"]
    distance = self.distance_3d(nav_pos, target_position)
    distance_band = self.classify_distance_to_band(distance, bands)

    centering_band = None
    roll_band = None
    centering_angle_deg = None
    roll_angle_deg = None
    attitude_condition = rule.get("attitude")
    if self.sim_mode != "beginners" and isinstance(attitude_condition, dict):
      target_quaternion = attitude_condition.get("quaternion")
      centering_bands = self.bands_from_band_objects(attitude_condition.get("centering_bands"), is_attitude=True)
      roll_bands = self.bands_from_band_objects(attitude_condition.get("roll_bands"), is_attitude=True)
      if target_quaternion and (centering_bands or roll_bands):
        centering_angle_deg, roll_angle_deg = self._evaluate_centering_and_roll(
          nav_pos, pose["quaternion"], marker_position, target_quaternion
        )
        if centering_bands:
          centering_band = self.classify_attitude_to_band(centering_angle_deg, centering_bands)
        if roll_bands:
          roll_band = self.classify_attitude_to_band(roll_angle_deg, roll_bands)

    band_candidates = [distance_band]
    if centering_band is not None:
      band_candidates.append(centering_band)
    if roll_band is not None:
      band_candidates.append(roll_band)
    selected_band = 0 if any(b == 0 for b in band_candidates) else min(band_candidates)

    detail = {
      "checkpoint_id": checkpoint_id,
      "sim_mode": self.sim_mode,
      "success": selected_band > 0,
      "timestamp": self.ros_time_string(),
      "current_position": pose["position"],
      "current_quaternion": pose["quaternion"],
      "target_position": target_position,
      "marker_position": marker_position,
      "distance": distance,
      "distance_band": distance_band,
      "centering_band": centering_band,
      "centering_angle_deg": centering_angle_deg,
      "roll_band": roll_band,
      "roll_angle_deg": roll_angle_deg,
      "selected_band": selected_band,
    }
    return selected_band > 0, "checkpoint validated" if selected_band > 0 else "checkpoint outside threshold", detail

  def get_checkpoint_rule(self, checkpoint_id):
    rule = self._checkpoint_rules.get(checkpoint_id)
    if rule is None:
      rule = self._checkpoint_rules.get(str(checkpoint_id))
    return rule

  def evaluate_goal_navigation(self):
    goal_checkpoint_id = self._goal_rule.get("checkpoint_id")
    if goal_checkpoint_id is None:
      return False, "goal checkpoint_id is not configured", None
    if self.get_checkpoint_rule(goal_checkpoint_id) is None:
      return False, "goal checkpoint_id is unknown", None
    return self.evaluate_checkpoint_navigation(goal_checkpoint_id)

  def build_checkpoint_passed_map(self):
    def sort_key(value):
      if isinstance(value, (int, float)):
        return (0, float(value))
      return (1, str(value))

    checkpoint_ids = self.get_checkpoint_id_list()
    passed_map = {}
    for checkpoint_id in sorted(checkpoint_ids, key=sort_key):
      checkpoint_key = str(checkpoint_id)
      detail = self.judge_state["checkpoints"].get(checkpoint_key)
      passed_map[checkpoint_key] = bool(detail and detail.get("success"))
    return passed_map

  def get_checkpoint_id_list(self):
    checkpoint_ids = list(self._checkpoint_rules.keys())
    if checkpoint_ids:
      return checkpoint_ids

    try:
      if os.path.exists(DEFAULT_MARKER_AREA_CONFIG_PATH):
        with open(DEFAULT_MARKER_AREA_CONFIG_PATH, "r", encoding="utf-8") as f:
          area_config = json.load(f)
        marker_ids = []
        for marker in area_config.get("UrdfMarkers", []):
          marker_id = marker.get("id")
          if marker_id is not None:
            marker_ids.append(marker_id)
        if marker_ids:
          return marker_ids
    except Exception as e:
      rospy.logwarn("Failed to load marker ids from area_config.json: {}".format(e))

    return []

  def sync_judge_report(self):
    checkpoint_passed = self.build_checkpoint_passed_map()
    checkpoint_detail = copy.deepcopy(self.judge_state["checkpoints"])

    def sort_key(value):
      if isinstance(value, (int, float)):
        return (0, float(value))
      return (1, str(value))

    checkpoint_ids = self.get_checkpoint_id_list()
    if not checkpoint_ids:
      checkpoint_ids = []
      for key in self.judge_state["checkpoints"].keys():
        try:
          checkpoint_ids.append(int(key))
        except Exception:
          checkpoint_ids.append(key)

    checkpoint_detail_list = []
    for checkpoint_id in sorted(checkpoint_ids, key=sort_key):
      checkpoint_key = str(checkpoint_id)
      detail = self.judge_state["checkpoints"].get(checkpoint_key, {})
      success = bool(detail.get("success", False))
      selected_band = detail.get(JSON_SELECTED_BAND)
      level = 0
      if success and selected_band is not None:
        try:
          level = int(selected_band)
        except Exception:
          level = 0

      checkpoint_detail_list.append({
        "checkpoint_id": checkpoint_id,
        "success": success,
        "level": level,
        "timestamp": detail.get("timestamp"),
        "reason": detail.get("reason", "not attempted"),
      })

    mission_start = self.judge_state["mission_start_ros_time"]
    mission_finish = self.judge_state["mission_finish_ros_time"]
    duration_sec = None
    if mission_start and mission_finish:
      try:
        start_dt = datetime.datetime.strptime(mission_start, "%Y%m%d %H%M%S%f")
        finish_dt = datetime.datetime.strptime(mission_finish, "%Y%m%d %H%M%S%f")
        duration_sec = round((finish_dt - start_dt).total_seconds(), 2)
      except Exception:
        duration_sec = None

    goal_detail = copy.deepcopy(self.judge_state["goal"])
    normalized_goal = {
      "success": bool(goal_detail.get("success", False)) if isinstance(goal_detail, dict) else False,
      "reason": goal_detail.get("reason") if isinstance(goal_detail, dict) else None,
      "timestamp": goal_detail.get("timestamp") if isinstance(goal_detail, dict) else None,
    }

    self.result_json["checkpoint_passed"] = checkpoint_passed
    self.result_json["checkpoint_passed_count"] = sum(1 for passed in checkpoint_passed.values() if passed)
    self.result_json["checkpoint_detail"] = checkpoint_detail

    self.result_json["JudgeReport"] = {
      "mission": {
        "started": self.judge_state["mission_started"],
        "finished": self.judge_state["mission_finished"],
        "start": mission_start,
        "finish": mission_finish,
        "duration_sec": duration_sec,
      },
      "checkpoint_detail": checkpoint_detail_list,
      "goal": normalized_goal,
      "events": copy.deepcopy(self.judge_state["events"]),
    }

  def build_result_output(self):
    return {
      RESULT_KEY.ILLEGAL: bool(self.result_json.get(RESULT_KEY.ILLEGAL, False)),
      "JudgeReport": copy.deepcopy(self.result_json.get("JudgeReport", {})),
    }

  def publish_checkpoint_result(self, checkpoint_id, success, selected_band=None):
    checkpoint_passed = self.build_checkpoint_passed_map()
    payload = {
      "status": JSON_STATUS_CHECKPOINT,
      "checkpoint_id": checkpoint_id,
      "success": bool(success),
      "checkpoint_passed": checkpoint_passed,
    }
    if selected_band is not None:
      payload[JSON_SELECTED_BAND] = int(selected_band)
    self.checkpoint_result_publisher.publish(json.dumps(payload, ensure_ascii=False))

  def publish_goal_result(self, success):
    payload = {
      "status": JSON_STATUS_FINISH,
      "success": bool(success),
    }
    self.goal_result_publisher.publish(json.dumps(payload, ensure_ascii=False))

  # Load the JSON file
  def load_json(self, path):
    with open(path, "r", encoding="utf-8") as file:
      return json.load(file)

  # Callback for JUDGE API messages
  def judge_callback(self, data):
    try:
      request = json.loads(data.data)
      if not isinstance(request, dict):
        raise ValueError("judge message must be a JSON object")
      self.parse_judge_msg(request)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
      rospy.logwarn("Ignoring invalid judge message: %s", error)

  # Callback for the Int-Ball2 self-position message
  def pose_callback(self, data):
    # Validate input
    if data is None:
      rospy.logwarn("Pose data is None.")
      return

    rospy.logdebug("Rcv Int-Ball2 pose")
    pose_msg = getattr(getattr(data, "pose", None), "pose", None)
    if pose_msg is not None:
      self.ib2_pose = pose_msg
      pos = [
        self.ib2_pose.position.x,
        self.ib2_pose.position.y,
        self.ib2_pose.position.z,
      ]
      ori = [
        self.ib2_pose.orientation.x,
        self.ib2_pose.orientation.y,
        self.ib2_pose.orientation.z,
        self.ib2_pose.orientation.w,
      ]
    else:
      self.ib2_pose = Pose()
      (pos, ori) = self.listener.lookupTransform("iss_body", "body", rospy.Time(0))
      self.ib2_pose.position.x = pos[0]
      self.ib2_pose.position.y = pos[1]
      self.ib2_pose.position.z = pos[2]
      self.ib2_pose.orientation.x = ori[0]
      self.ib2_pose.orientation.y = ori[1]
      self.ib2_pose.orientation.z = ori[2]
      self.ib2_pose.orientation.w = ori[3]

    # Convert Int-Ball2's attitude to a rotation matrix -> (A)
    rot_vec = tf.transformations.quaternion_matrix(ori)

    # Rotate the unit vector to match Int-Ball2's attitude -> (B)
    unit_coordinate_rotated = np.dot(rot_vec, self.unit_vec.reshape(4,1) )

    # Compute the main camera position
    navcam_def_coordinate_rotated = np.dot(rot_vec, self.navcam_def.reshape(4,1))
    navcam_pos = pos + navcam_def_coordinate_rotated[:3].reshape(3)

    # Register (B) with TF (Int-Ball2's direction vector) -> (D)
    self.broadcaster.sendTransform(unit_coordinate_rotated[:3],
                          ori,
                          rospy.Time.now(),
                          TF_FRAME_VEC1,
                          TF_FRAME_BASE)

    # Register the main camera position with TF -> (E)
    self.broadcaster.sendTransform(navcam_pos,
                          ori,
                          rospy.Time.now(),
                          TF_FRAME_VEC0,
                          TF_FRAME_BASE)

    # for debug
    if self.debug:
      self.marker_tool.publish_marker(id=10, position=pos, pose=ori, color=(1,0,0), size=(0.3,0.3,0.3), marker_type=1, pose_type='qua')
      self.marker_tool.publish_marker(30, position=navcam_pos, pose=ori, color=(1,0,0), size=(5,0.01,0.01), marker_type=0, pose_type='qua')

    rate = rospy.Rate(5)
    rate.sleep()

  # Periodically save Int-Ball2's self-position
  def save_pose_to_file(self):
    try:
      mode = "a"
      if not self.gameHasStarted:
        mode = "w"

      with open(self.pose_path, mode) as file:
        while not rospy.is_shutdown() and not self.stop_thread.is_set():
          if self.ib2_pose is not None:
            pos = self.ib2_pose.position
            ori = self.ib2_pose.orientation
            pose_data = {
                'position': [pos.x, pos.y, pos.z],
                'orientation': [ori.x, ori.y, ori.z, ori.w]
            }
            file.write(json.dumps(pose_data) + "\n")
          else:
            file.write('{"position": null}\n')

          rospy.sleep(T_CYCLE)
    except Exception as e:
      rospy.logerr(f"Error while writing to pose file: {e}")

  # Callback for the illegal-detection message
  def illegal_callback(self, data):

    # Set illegal to true when unauthorized access to the ground truth is detected
    self.result_json[RESULT_KEY.ILLEGAL] = True
    rospy.logwarn('Illegal detection msg is recieved.')
    self.output_result()

  # Entry point for JUDGE API processing
  def parse_judge_msg(self, data):

    # Validate input
    if data is None:
      rospy.logwarn("Request data is None.")
      return

    # Record raw data
    self.output_row(data)

    # First get the payload and timestamp
    status = data.get(JSON_STATUS, None)

    if self.test_mode:
      # Original behavior: get the time sent from the APK
      timestamp = data.get(JSON_TIMESTAMP, None)
    else:
      # Updated behavior: get the time from ROS.
      received_time = rospy.Time.now()
      timestamp = datetime.datetime.fromtimestamp(received_time.to_sec()).strftime("%Y%m%d %H%M%S%f")[:-3] # in milli seconds"


    # Process each payload
    if status is not None:
      rospy.loginfo("status arrived: {}".format(status))

    if(status == JSON_STATUS_START):
      # START
      self.judge_start(timestamp)

    elif(status == JSON_STATUS_CHECKPOINT):
      self.judge_checkpoint_passed(timestamp, data)

    #elif(status == UNDOCK_START):
    #  self.judge_undock()

    elif(status == JSON_STATUS_FINISH):
      # FINISH
      self.judge_finish(timestamp)

    elif(status == JSON_ROUNDING_COMPLETE):
      # ROUNDING IS COMPLETE
      self.report_rounding_completion(timestamp)

    failed = data.get(JSON_FAILED, None)

    if failed is not None:
      rospy.logerr("Simulator failed to start: {}".format(failed))
      with open(FAILED_FILE_NAME, 'w') as f:
        f.write("kibo_rpc_api: {}".format(failed))
        f.close()
        self.exit_judge()

  # Processing on receipt of the START API
  def judge_start(self, timestamp):
    if(not self.gameHasStarted):
      self.result_json[RESULT_KEY.MISSIONTIME]["start"] = timestamp # in milli seconds"

      self.judge_state["mission_started"] = True
      self.judge_state["mission_start_ros_time"] = timestamp
      self.judge_state["events"].append({
        "status": JSON_STATUS_START,
        "timestamp": timestamp,
      })
      self.sync_judge_report()

      # Write out the file
      self.output_result()
      # Start a thread that appends the pose to the file every 0.1 seconds
      if self.thread is None or not self.thread.is_alive():
        self.stop_thread.clear()
        self.thread = threading.Thread(target=self.save_pose_to_file)
        self.thread.start()

      self.gameHasStarted = True

    else:
      rospy.logwarn('JudgeSendStart has already called.')

  def judge_checkpoint_passed(self, timestamp, data):
    if not self.gameHasStarted:
      rospy.logwarn('checkpoint event received before mission start')
      return
    if self.finishflag:
      rospy.logwarn('checkpoint event received after mission finish')
      return

    checkpoint_id = data.get("checkpoint_id")
    if checkpoint_id is None:
      rospy.logwarn('checkpoint event missing checkpoint_id')
      return

    checkpoint_key = str(checkpoint_id)
    if checkpoint_key in self.judge_state["checkpoints"]:
      rospy.logwarn('checkpoint {} already processed'.format(checkpoint_id))
      return

    success, reason, detail = self.evaluate_checkpoint_navigation(checkpoint_id)
    event_detail = detail if isinstance(detail, dict) else {"reason": reason}
    event_detail["timestamp"] = timestamp
    event_detail["reason"] = reason
    self.judge_state["checkpoints"][checkpoint_key] = event_detail
    self.judge_state["events"].append({
      "status": JSON_STATUS_CHECKPOINT,
      "timestamp": timestamp,
      "checkpoint_id": checkpoint_id,
      "success": success,
      "reason": reason,
    })
    self.sync_judge_report()
    selected_band = None
    if isinstance(event_detail, dict):
      selected_band = event_detail.get(JSON_SELECTED_BAND)
    self.publish_checkpoint_result(checkpoint_id, success, selected_band)
    self.output_result()
  #def judge_undock(self):
  #  if(not self.gameHasStarted):
  #    if self.ib2HasMoved:
  #      # Check whether it was moving before undocking
  #      self.ib2MovedBeforeUndocking = True

  # Processing on receipt of the FINISH API
  def judge_finish(self, timestamp):
    if not self.gameHasStarted:
      rospy.logwarn('finish event received before mission start')
      return
    if self.finishflag:
      rospy.logwarn('finish event received after mission finish')
      return

    goal_checkpoint_id = self._goal_rule.get("checkpoint_id")
    checkpoint_key = str(goal_checkpoint_id)
    existing_detail = self.judge_state["checkpoints"].get(checkpoint_key)
    if isinstance(existing_detail, dict) and existing_detail.get("success", False):
      success = True
      reason = "goal checkpoint previously passed"
      detail = copy.deepcopy(existing_detail)
      detail["previously_passed"] = True
      detail["evaluated_at_finish"] = False
    elif self.get_checkpoint_rule(goal_checkpoint_id) is None:
      success = False
      reason = "goal checkpoint_id is not configured or unknown"
      detail = {"goal_checkpoint_id": goal_checkpoint_id}
    else:
      success, reason, detail = self.evaluate_checkpoint_navigation(goal_checkpoint_id)
      detail = detail if isinstance(detail, dict) else {"reason": reason}
      detail["goal_checkpoint_id"] = goal_checkpoint_id
      detail["previously_passed"] = False
      detail["evaluated_at_finish"] = True
      if success:
        self.judge_state["checkpoints"][checkpoint_key] = detail

    goal_detail = detail if isinstance(detail, dict) else {"reason": reason}
    goal_detail["timestamp"] = timestamp
    goal_detail["reason"] = reason
    self.judge_state["goal"] = goal_detail
    self.result_json[RESULT_KEY.ROUNDING_REPORT][RESULT_KEY.TIMESTAMP] = timestamp
    self.result_json[RESULT_KEY.ROUNDING_REPORT][RESULT_KEY.ARRIVAL][RESULT_KEY.REPORT_TRY] = True
    self.result_json[RESULT_KEY.ROUNDING_REPORT][RESULT_KEY.ARRIVAL][RESULT_KEY.REPORT_SUCCESS] = success
    self.result_json[RESULT_KEY.ROUNDING_REPORT][RESULT_KEY.ARRIVAL][RESULT_KEY.DISTANCE] = goal_detail.get("distance", 0)
    self.publish_goal_result(success)

    self.finishflag = 1
    self.result_json[RESULT_KEY.MISSIONTIME]["finish"] = timestamp # in milli seconds"
    self.result_json[RESULT_KEY.FOUND_REPORT][RESULT_KEY.TIMESTAMP] = timestamp # in milli seconds"
    self.result_json[RESULT_KEY.FOUND_REPORT][RESULT_KEY.CAMERA_ANGLE] = 0
    self.result_json[RESULT_KEY.FOUND_REPORT][RESULT_KEY.DISTANCE] = 0
    self.result_json[RESULT_KEY.FOUND_REPORT][RESULT_KEY.REPORT_TRY] = self.judge_state["goal"] is not None
    self.result_json[RESULT_KEY.FOUND_REPORT][RESULT_KEY.REPORT_SUCCESS] = bool(self.judge_state["goal"] and self.judge_state["goal"].get("success"))
    self.judge_state["mission_finished"] = True
    self.judge_state["mission_finish_ros_time"] = timestamp
    self.judge_state["events"].append({
      "status": JSON_STATUS_FINISH,
      "timestamp": timestamp,
    })
    self.sync_judge_report()

    # Stop the thread that appends the pose to the file every 0.1 seconds
    self.stop_thread.set()
    if self.thread is not None:
        self.thread.join()

    # Write out the file
    self.output_result_finish()

  # Processing on receipt of ROUNDING COMPLETE
  def report_rounding_completion(self, timestamp):
    rospy.logwarn("Rounding Complete is ignored; goal evaluation is performed by Mission Finish")

  # Write the raw message data out to a file
  def output_row(self, data):
    self.row_f.write(str(data))
    self.row_f.write("\n")

  # Write the scoring result out to a file
  def output_result(self):
    f = open(self.result_path, "w")
    output_payload = self.build_result_output()
    rospy.logwarn(self.result_path)
    rospy.logwarn(output_payload)
    json.dump(output_payload, f, indent=4, sort_keys=False, separators=(',', ': '))
    f.close()

  # Write the scoring result out to a file
  def output_result_finish(self):
    f = open(self.result_path, "w")
    output_payload = self.build_result_output()
    json.dump(output_payload, f, indent=4, sort_keys=False, separators=(',', ': '))
    f.close()
    f = open(self.finish_path, "w")
    f.close()
    self.exit_judge()

  # Finish the scoring program
  def exit_judge(self):
    rospy.loginfo("Finish judge")
    rospy.signal_shutdown("")

  # Processing on shutdown
  def shutdown_hook(self):
    try:
      if (not self.score_api_final_sent) and SCORE_API_URL:
        requests.post(
          SCORE_API_URL,
          json=self.build_result_output(),
          timeout=5,
        ).raise_for_status()
        self.score_api_final_sent = True
        rospy.loginfo("Sent the result")
    except Exception as e:
        rospy.logerr(f"Failed to send the result: {e}")

    # Close the raw data file stream
    self.row_f.close()
    # Stop the pose-saving thread
    self.stop_thread.set()
    if self.thread is not None:
        self.thread.join()
    rospy.loginfo("Shutdown Judge node ...")

if __name__ == '__main__':
  rospy.init_node('kibo_rpc_judge')

  parser = argparse.ArgumentParser()
  parser.add_argument('-c', '--cheatsheet_path', default=DEFAULT_CHEATSHEET_PATH)
  parser.add_argument('-o', '--output_dir', default=DEFAULT_OUTPUT_DIR)
  parser.add_argument('-f', '--result', default=DEFAULT_RESULT_FILE_NAME)
  parser.add_argument('-i', '--finish', default=DEFAULT_FINISH_FILE_NAME)
  parser.add_argument('-r', '--row', default=DEFAULT_ROW_FILE_NAME)
  parser.add_argument('-d', '--debug', action='store_true')
  parser.add_argument('-t', '--test_mode', action='store_true')
  args = parser.parse_args()

  rospy.loginfo("CHEAT SHEET PATH  : {0}".format(args.cheatsheet_path))
  rospy.loginfo("OUTPUT DIRECTORY  : {0}".format(args.output_dir))
  rospy.loginfo("RESULT FILE NAME  : {0}".format(args.result))
  rospy.loginfo("FINISH FILE NAME  : {0}".format(args.finish))
  rospy.loginfo("ROW DATA FILE NAME: {0}".format(args.row))
  rospy.loginfo("DEBUG_MODE: {0}".format(args.debug))
  rospy.loginfo("TEST_MODE: {0}".format(args.test_mode))

  # Create the scoring instance
  referee = Referee(args.cheatsheet_path, args.output_dir, args.result, args.finish, args.row, args.debug)
  referee.test_mode = args.test_mode

  # Subscribers
  rospy.Subscriber("/gs/data", String, referee.judge_callback, queue_size=20)
  rospy.Subscriber("/sensor_fusion/navigation", Navigation, referee.pose_callback, queue_size=1)
  rospy.Subscriber("/krpc/comm/illegal", Bool, referee.illegal_callback, queue_size=3)

  # Wait briefly (for subscribers to connect)
  r = rospy.Rate(5)
  r.sleep()
  rospy.set_param("/krpc/judge_ready", True)

  rospy.loginfo("Judge Ready")
  rospy.spin()

  exit(referee.status)

