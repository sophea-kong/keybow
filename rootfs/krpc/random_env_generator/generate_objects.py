#! /usr/bin/env python3

####################
# Generate objects #
####################
# Generate cheat_sheet.json with checkpoint information from area_config.json UrdfMarkers.

import os
import json
import random
import copy
import transformations
import math
from argparse import ArgumentParser
from typing import List, Tuple

# Const Values
INPUT_RELATIVE_DIR   = 'files/input'
INPUT_AREA_CONFIG    = os.path.join(INPUT_RELATIVE_DIR, 'area_config.json')

DEFAULT_CHECKPOINT_SCORE_BANDS = [
    {"radius": 0.2, "level": 3},
    {"radius": 0.4, "level": 2},
    {"radius": 0.6, "level": 1},
]

DEFAULT_CHECKPOINT_DISTANCE = 0.5
DEFAULT_CHECKPOINT_YAW_MIN_DEG = -20.0
DEFAULT_CHECKPOINT_YAW_MAX_DEG = 20.0
DEFAULT_CHECKPOINT_PITCH_MIN_DEG = -15.0
DEFAULT_CHECKPOINT_PITCH_MAX_DEG = 15.0
DEFAULT_CHECKPOINT_ROLL_MIN_DEG = -180.0
DEFAULT_CHECKPOINT_ROLL_MAX_DEG = 180.0

DEFAULT_ATTITUDE_BANDS = [
    {'angle': 10.0, 'level': 3},
    {'angle': 20.0, 'level': 2},
    {'angle': 30.0, 'level': 1},
]

# Range in which checkpoints may be placed (DS coordinate system [m]). Can be overridden by SafeArea in area_config.json.
DEFAULT_SAFE_AREA = {
    'min': [0.20, -0.80, 0.00],
    'max': [7.00, 0.85, 1.68],
}
SAFE_AREA_MAX_RETRY = 50

GOAL_MARKER_ID = 12
GOAL_DISTANCE_TH = 0.3

# Difficulty presets: number of checkpoints to include (goal marker is always included)
DIFFICULTY_PRESETS = {
    'easy': 6,
    'normal': 8,
    'hard': 10,
    'veryhard': 12,
}

def get_current_abspath() -> str:
    current_abspath = os.path.dirname(os.path.abspath(__file__))
    return current_abspath

def get_full_abspath(relative_path:str) -> str:
    full_abspath = os.path.join(get_current_abspath(),relative_path)
    return full_abspath

def load_json(path:str) -> dict or list:
    with open(path, "r") as f:
        data = json.load(f)
    return data

def write_json(path:str, json_dict:dict) -> None:
    with open(path, "w") as f:
        json.dump(json_dict, f, indent=4)

def normalize_checkpoint_score_bands(score_bands) -> list:
    normalized = []
    if not isinstance(score_bands, list):
        return normalized

    for band in score_bands:
        if not isinstance(band, dict):
            continue
        threshold = band.get('radius', band.get('margin', band.get('distance')))
        score = band.get('level', band.get('score', band.get('point', band.get('points'))))
        if threshold is None or score is None:
            continue
        try:
            normalized.append({
                'radius': float(threshold),
                'level': int(score),
            })
        except Exception:
            continue

    normalized.sort(key=lambda x: x['radius'])
    return normalized

def normalize_attitude_bands(attitude_bands) -> list:
    normalized = []
    if not isinstance(attitude_bands, list):
        return normalized

    for band in attitude_bands:
        if not isinstance(band, dict):
            continue
        angle = band.get('angle', band.get('margin', band.get('threshold')))
        score = band.get('level', band.get('score', band.get('point', band.get('points'))))
        try:
            angle = float(angle)
            score = int(score)
        except (TypeError, ValueError):
            continue
        normalized.append({'angle': angle, 'level': score})

    normalized.sort(key=lambda x: x['angle'])
    return normalized

def ensure_three_level_score_bands(score_bands:list, context_label:str) -> list:
    if len(score_bands) != 3:
        raise ValueError(f'{context_label} must define exactly 3 score bands')
    return score_bands

def resolve_checkpoint_score_bands_for_marker(marker:dict, area_config:dict) -> list:
    if not isinstance(marker, dict):
        raise ValueError('UrdfMarkers must contain dict items')

    marker_id = marker.get('id', 'unknown')

    for key in ('score_bands', 'scoreBands', 'bands'):
        bands = normalize_checkpoint_score_bands(marker.get(key))
        if bands:
            return ensure_three_level_score_bands(bands, f'UrdfMarkers[id={marker_id}].{key}')

    raise ValueError(f'UrdfMarkers[id={marker_id}] must define score_bands (3 levels)')

def resolve_angle_bands_for_marker(marker:dict, area_config:dict, marker_keys, area_config_key, label:str) -> list:
    marker_id = marker.get('id', '?') if isinstance(marker, dict) else '?'
    for key in marker_keys:
        bands = normalize_attitude_bands(marker.get(key))
        if bands:
            return bands

    bands = normalize_attitude_bands(area_config.get(area_config_key)) if isinstance(area_config, dict) else []
    if bands:
        return bands

    bands = normalize_attitude_bands(DEFAULT_ATTITUDE_BANDS)
    if bands:
        return bands

    raise ValueError(f'UrdfMarkers[id={marker_id}] failed to resolve {label}')

def resolve_centering_bands_for_marker(marker:dict, area_config:dict) -> list:
    return resolve_angle_bands_for_marker(
        marker, area_config, ('centering_bands', 'centeringBands'), 'centering_bands', 'centering_bands'
    )

def resolve_roll_bands_for_marker(marker:dict, area_config:dict) -> list:
    return resolve_angle_bands_for_marker(
        marker, area_config, ('roll_bands', 'rollBands'), 'roll_bands', 'roll_bands'
    )

def resolve_checkpoint_sampling_params(config:dict, args) -> dict:
    # Priority: CLI args > area_config CheckpointGeneration > defaults
    generation = config.get('CheckpointGeneration', {})
    if not isinstance(generation, dict):
        generation = {}

    distance = generation.get('distance', DEFAULT_CHECKPOINT_DISTANCE)
    yaw_min = generation.get('yaw_min_deg', DEFAULT_CHECKPOINT_YAW_MIN_DEG)
    yaw_max = generation.get('yaw_max_deg', DEFAULT_CHECKPOINT_YAW_MAX_DEG)
    pitch_min = generation.get('pitch_min_deg', DEFAULT_CHECKPOINT_PITCH_MIN_DEG)
    pitch_max = generation.get('pitch_max_deg', DEFAULT_CHECKPOINT_PITCH_MAX_DEG)
    roll_min = generation.get('roll_min_deg', DEFAULT_CHECKPOINT_ROLL_MIN_DEG)
    roll_max = generation.get('roll_max_deg', DEFAULT_CHECKPOINT_ROLL_MAX_DEG)

    if args.checkpoint_distance is not None:
        distance = args.checkpoint_distance
    if args.checkpoint_yaw_min_deg is not None:
        yaw_min = args.checkpoint_yaw_min_deg
    if args.checkpoint_yaw_max_deg is not None:
        yaw_max = args.checkpoint_yaw_max_deg
    if args.checkpoint_pitch_min_deg is not None:
        pitch_min = args.checkpoint_pitch_min_deg
    if args.checkpoint_pitch_max_deg is not None:
        pitch_max = args.checkpoint_pitch_max_deg
    if args.checkpoint_roll_min_deg is not None:
        roll_min = args.checkpoint_roll_min_deg
    if args.checkpoint_roll_max_deg is not None:
        roll_max = args.checkpoint_roll_max_deg

    distance = float(distance)
    yaw_min = float(yaw_min)
    yaw_max = float(yaw_max)
    pitch_min = float(pitch_min)
    pitch_max = float(pitch_max)
    roll_min = float(roll_min)
    roll_max = float(roll_max)

    if yaw_min > yaw_max:
        yaw_min, yaw_max = yaw_max, yaw_min
    if pitch_min > pitch_max:
        pitch_min, pitch_max = pitch_max, pitch_min
    if roll_min > roll_max:
        roll_min, roll_max = roll_max, roll_min

    return {
        'distance': distance,
        'yaw_min_deg': yaw_min,
        'yaw_max_deg': yaw_max,
        'pitch_min_deg': pitch_min,
        'pitch_max_deg': pitch_max,
        'roll_min_deg': roll_min,
        'roll_max_deg': roll_max,
    }

def normalize_quaternion(quaternion) -> list:
    if not isinstance(quaternion, list) or len(quaternion) < 4:
        return [0.0, 0.0, 0.0, 1.0]
    qx = float(quaternion[0])
    qy = float(quaternion[1])
    qz = float(quaternion[2])
    qw = float(quaternion[3])
    norm = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
    if norm <= 0.0:
        return [0.0, 0.0, 0.0, 1.0]
    return [qx / norm, qy / norm, qz / norm, qw / norm]

def quaternion_multiply(q1:list, q2:list) -> list:
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return [
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
    ]

def vector_norm(v:list) -> float:
    return math.sqrt(float(v[0]) * float(v[0]) + float(v[1]) * float(v[1]) + float(v[2]) * float(v[2]))

def normalize_vector(v:list, fallback=None) -> list:
    if fallback is None:
        fallback = [1.0, 0.0, 0.0]
    n = vector_norm(v)
    if n <= 0.0:
        return [float(fallback[0]), float(fallback[1]), float(fallback[2])]
    return [float(v[0]) / n, float(v[1]) / n, float(v[2]) / n]

def vector_cross(a:list, b:list) -> list:
    return [
        float(a[1]) * float(b[2]) - float(a[2]) * float(b[1]),
        float(a[2]) * float(b[0]) - float(a[0]) * float(b[2]),
        float(a[0]) * float(b[1]) - float(a[1]) * float(b[0]),
    ]

def vector_dot(a:list, b:list) -> float:
    return float(a[0]) * float(b[0]) + float(a[1]) * float(b[1]) + float(a[2]) * float(b[2])

def quaternion_from_axis_angle(axis:list, angle_rad:float) -> list:
    axis_n = normalize_vector(axis)
    half = 0.5 * float(angle_rad)
    s = math.sin(half)
    c = math.cos(half)
    return [axis_n[0] * s, axis_n[1] * s, axis_n[2] * s, c]

def quaternion_from_forward_axis(forward_world:list) -> list:
    x_axis = normalize_vector(forward_world)
    tmp_up = [0.0, 0.0, 1.0]
    if abs(vector_dot(x_axis, tmp_up)) > 0.95:
        tmp_up = [0.0, 1.0, 0.0]
    z_axis = normalize_vector(vector_cross(x_axis, tmp_up), fallback=[0.0, 0.0, 1.0])
    y_axis = normalize_vector(vector_cross(z_axis, x_axis), fallback=[0.0, 1.0, 0.0])

    rot = [
        [x_axis[0], y_axis[0], z_axis[0], 0.0],
        [x_axis[1], y_axis[1], z_axis[1], 0.0],
        [x_axis[2], y_axis[2], z_axis[2], 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
    return normalize_quaternion(transformations.quaternion_from_matrix(rot).tolist())

def rotate_vector_by_quaternion(vector:list, quaternion:list) -> list:
    q = normalize_quaternion(quaternion)
    q_conj = [-q[0], -q[1], -q[2], q[3]]
    vq = [float(vector[0]), float(vector[1]), float(vector[2]), 0.0]
    rotated = quaternion_multiply(quaternion_multiply(q, vq), q_conj)
    return [rotated[0], rotated[1], rotated[2]]

def _checkpoint_direction_override(marker_id) -> list:
    return None

def normalize_safe_area(value) -> dict:
    if not isinstance(value, dict):
        return None

    lower = value.get('min')
    upper = value.get('max')
    if not isinstance(lower, list) or not isinstance(upper, list):
        return None
    if len(lower) < 3 or len(upper) < 3:
        return None

    lower = [float(lower[i]) for i in range(3)]
    upper = [float(upper[i]) for i in range(3)]
    for i in range(3):
        if lower[i] > upper[i]:
            lower[i], upper[i] = upper[i], lower[i]
    return {'min': lower, 'max': upper}

def resolve_safe_area(config:dict) -> dict:
    # Priority: area_config SafeArea > default. Can be disabled with "SafeArea": null.
    if isinstance(config, dict) and 'SafeArea' in config:
        return normalize_safe_area(config.get('SafeArea'))
    return normalize_safe_area(DEFAULT_SAFE_AREA)

def is_inside_safe_area(position:list, safe_area:dict) -> bool:
    lower = safe_area['min']
    upper = safe_area['max']
    return all(lower[i] <= float(position[i]) <= upper[i] for i in range(3))

def clamp_to_safe_area(position:list, safe_area:dict) -> list:
    lower = safe_area['min']
    upper = safe_area['max']
    return [min(max(float(position[i]), lower[i]), upper[i]) for i in range(3)]

def sample_checkpoint_position_once(marker_id, marker_position:list, marker_quaternion:list, sampling_params:dict) -> list:
    override_dir = _checkpoint_direction_override(marker_id)
    if override_dir is not None:
        displacement_dir = normalize_vector(override_dir)
    else:
        yaw_deg = random.uniform(sampling_params['yaw_min_deg'], sampling_params['yaw_max_deg'])
        pitch_deg = random.uniform(sampling_params['pitch_min_deg'], sampling_params['pitch_max_deg'])
        yaw = math.radians(yaw_deg)
        pitch = math.radians(pitch_deg)

        local_dir = [
            math.cos(pitch) * math.sin(yaw),
            math.sin(pitch),
            math.cos(pitch) * math.cos(yaw),
        ]
        world_dir = rotate_vector_by_quaternion(local_dir, marker_quaternion)
        displacement_dir = world_dir

    distance = sampling_params['distance']
    return [
        float(marker_position[0]) + distance * displacement_dir[0],
        float(marker_position[1]) + distance * displacement_dir[1],
        float(marker_position[2]) + distance * displacement_dir[2],
    ]

def sample_checkpoint_position(marker_id, marker_position:list, marker_quaternion:list, sampling_params:dict, safe_area:dict=None) -> list:
    if safe_area is None:
        return sample_checkpoint_position_once(marker_id, marker_position, marker_quaternion, sampling_params)

    for _ in range(SAFE_AREA_MAX_RETRY):
        position = sample_checkpoint_position_once(marker_id, marker_position, marker_quaternion, sampling_params)
        if is_inside_safe_area(position, safe_area):
            return position

    # Remove the spread and fall back to directly in front of the marker
    straight_params = dict(sampling_params)
    straight_params.update({
        'yaw_min_deg': 0.0,
        'yaw_max_deg': 0.0,
        'pitch_min_deg': 0.0,
        'pitch_max_deg': 0.0,
    })
    position = sample_checkpoint_position_once(marker_id, marker_position, marker_quaternion, straight_params)
    if is_inside_safe_area(position, safe_area):
        print(f'[generate_objects] marker {marker_id}: checkpoint fell back to marker-forward direction (safe area)')
        return position

    clamped = clamp_to_safe_area(position, safe_area)
    print(f'[generate_objects] WARNING: marker {marker_id}: checkpoint clamped into safe area {position} -> {clamped}')
    return clamped

def sample_checkpoint_attitude_quaternion(checkpoint_position:list, marker_position:list, sampling_params:dict) -> list:
    forward_world = [
        float(marker_position[0]) - float(checkpoint_position[0]),
        float(marker_position[1]) - float(checkpoint_position[1]),
        float(marker_position[2]) - float(checkpoint_position[2]),
    ]
    forward_world = normalize_vector(forward_world, fallback=[1.0, 0.0, 0.0])

    base_q = quaternion_from_forward_axis(forward_world)
    roll_deg = random.uniform(sampling_params['roll_min_deg'], sampling_params['roll_max_deg'])
    roll_q = quaternion_from_axis_angle(forward_world, math.radians(roll_deg))
    return normalize_quaternion(quaternion_multiply(roll_q, base_q))

def select_markers_by_difficulty(markers:list, level:str, goal_checkpoint_id:int) -> list:
    max_checkpoints = DIFFICULTY_PRESETS.get(level, DIFFICULTY_PRESETS['normal'])

    goal_marker = None
    other_markers = []
    for marker in markers:
        if not isinstance(marker, dict):
            continue
        if marker.get('id') == goal_checkpoint_id:
            goal_marker = marker
        else:
            other_markers.append(marker)

    if goal_marker is None:
        raise ValueError(f'UrdfMarkers does not include goal marker id: {goal_checkpoint_id}')

    # goal marker is always included; fill remaining slots from other markers
    slots = max_checkpoints - 1
    if slots >= len(other_markers):
        selected = other_markers[:]
    else:
        selected = random.sample(other_markers, slots)

    selected.append(goal_marker)
    return selected

def build_checkpoints_from_urdf_markers(markers:list, area_config:dict, sampling_params:dict, goal_checkpoint_id:int) -> Tuple[list, dict]:
    checkpoints = []
    goal_pose = None
    safe_area = resolve_safe_area(area_config)
    if safe_area is None:
        print('[generate_objects] safe area is disabled')
    else:
        print(f'[generate_objects] safe area: min={safe_area["min"]} max={safe_area["max"]}')
    found_goal_checkpoint = False

    for marker in markers:
        if not isinstance(marker, dict):
            continue
        marker_id = marker.get('id')
        position = marker.get('position')
        quaternion = marker.get('quaternion', [0.0, 0.0, 0.0, 1.0])
        if marker_id is None or not isinstance(position, list) or len(position) < 3:
            continue

        marker_quaternion = [
            float(quaternion[0]),
            float(quaternion[1]),
            float(quaternion[2]),
            float(quaternion[3]),
        ]
        marker_position = [float(position[0]), float(position[1]), float(position[2])]
        checkpoint_position_absolute = sample_checkpoint_position(marker_id, marker_position, marker_quaternion, sampling_params, safe_area)
        checkpoint_position_relative_global = [
            checkpoint_position_absolute[i] - marker_position[i] for i in range(3)
        ]
        marker_quaternion_inv = [-marker_quaternion[0], -marker_quaternion[1], -marker_quaternion[2], marker_quaternion[3]]
        checkpoint_position_local = rotate_vector_by_quaternion(checkpoint_position_relative_global, marker_quaternion_inv)
        checkpoint_quaternion = sample_checkpoint_attitude_quaternion(checkpoint_position_absolute, marker_position, sampling_params)
        marker_score_bands = resolve_checkpoint_score_bands_for_marker(marker, area_config)
        marker_centering_bands = resolve_centering_bands_for_marker(marker, area_config)
        marker_roll_bands = resolve_roll_bands_for_marker(marker, area_config)

        if int(marker_id) == goal_checkpoint_id:
            found_goal_checkpoint = True

        checkpoints.append({
            'checkpointid': int(marker_id),
            'position': checkpoint_position_absolute,
            'marker_pose': {
                'position': marker_position,
                'quaternion': marker_quaternion,
            },
            'score_bands': marker_score_bands,
            'attitude': {
                'quaternion': checkpoint_quaternion,
                'centering_bands': marker_centering_bands,
                'roll_bands': marker_roll_bands,
            },
        })

    checkpoints.sort(key=lambda x: x.get('checkpointid', 0))
    if not found_goal_checkpoint:
        raise ValueError(f'UrdfMarkers does not include goal marker id: {goal_checkpoint_id}')

    goal = {
        'checkpoint_id': goal_checkpoint_id,
        'all_checkpoints_bonus': 0,
    }
    return checkpoints, goal

def parse_args():
    argparser = ArgumentParser()
    argparser.add_argument('-r', '--round', type=str,
                           default="simulation",
                           help='Name of round')
    argparser.add_argument('-c', '--count', type=int,
                           default=1,
                           help='Count of game objects variation')
    argparser.add_argument('-l', '--levels', type=str,
                           default='normal',
                           choices=list(DIFFICULTY_PRESETS.keys()),
                           help='Difficulty level (controls checkpoint count and thresholds)')
    argparser.add_argument('-o', '--output_dir', type=str,
                           default=None,
                           help='Output directory for generated files (default: ./files/{round})')
    argparser.add_argument('--checkpoint-distance', type=float,
                           default=None,
                           help='Distance from AR marker to checkpoint position [m]')
    argparser.add_argument('--checkpoint-yaw-min-deg', type=float,
                           default=None,
                           help='Minimum yaw offset from marker forward axis [deg]')
    argparser.add_argument('--checkpoint-yaw-max-deg', type=float,
                           default=None,
                           help='Maximum yaw offset from marker forward axis [deg]')
    argparser.add_argument('--checkpoint-pitch-min-deg', type=float,
                           default=None,
                           help='Minimum pitch offset from marker forward axis [deg]')
    argparser.add_argument('--checkpoint-pitch-max-deg', type=float,
                           default=None,
                           help='Maximum pitch offset from marker forward axis [deg]')
    argparser.add_argument('--checkpoint-roll-min-deg', type=float,
                           default=None,
                           help='Minimum roll angle around marker-camera line [deg]')
    argparser.add_argument('--checkpoint-roll-max-deg', type=float,
                           default=None,
                           help='Maximum roll angle around marker-camera line [deg]')
    argparser.add_argument('--goal-checkpoint-id', type=int,
                           default=GOAL_MARKER_ID,
                           help='AR marker/checkpoint ID to include as the final checkpoint')

    args = argparser.parse_args()

    assert args.round != '', 'Please specify the round. Your input is empty value.'
    assert args.count > 0,  f'Count of game objects variation is invalid value({args.count} > 0).'
    if args.checkpoint_distance is not None:
        assert args.checkpoint_distance > 0.0, 'checkpoint distance must be > 0'
    return args

def main():
    args = parse_args()

    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = f'./files/{args.round}'

    os.makedirs(output_dir, exist_ok=True)
    os.chdir(get_current_abspath())

    for index in range(args.count):
        area_config = load_json(INPUT_AREA_CONFIG)
        checkpoint_sampling_params = resolve_checkpoint_sampling_params(area_config, args)

        all_markers = area_config.get('UrdfMarkers', [])
        selected_markers = select_markers_by_difficulty(all_markers, args.levels, args.goal_checkpoint_id)

        checkpoints, goal = build_checkpoints_from_urdf_markers(
            selected_markers, area_config, checkpoint_sampling_params, args.goal_checkpoint_id
        )

        generated_cheat_sheet = {
            'RandomSeed': random.randint(0, 2**32 - 1),
            'Level': args.levels,
            'Checkpoints': checkpoints,
            'Goal': goal,
        }

        output_cheat_sheet = os.path.join(output_dir, f'cheat_sheet_{str(index + 1).zfill(2)}.json')
        write_json(output_cheat_sheet, generated_cheat_sheet)

if __name__ == '__main__':
    main()
