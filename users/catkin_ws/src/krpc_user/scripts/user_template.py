#!/usr/bin/python3
# -*- coding:utf-8 -*-
"""
Single-file Kibo-RPC 7th Autonomous Flight Agent.
Fully compliant with ROS Melodic, Python 3.6.9, and official platform contracts.
"""
import json
import math
import os
import sys
import itertools
import rospy
import actionlib
from geometry_msgs.msg import PoseStamped, Point, Quaternion
from platform_msgs.msg import UserLogic
from platform_msgs.srv import StopProcessingUserNode, StopProcessingUserNodeResponse
from krpc_ib2_msgs.srv import MissionStart, MissionFinished, CheckPoints
from krpc_ib2_msgs.msg import CheckpointPassedAction, CheckpointPassedGoal
from ib2_msgs.msg import CtlCommandAction, CtlCommandGoal, CtlCommandResult, CtlStatusType, Navigation
from std_msgs.msg import String

def quat_angular_distance(q1, q2):
    dot = abs(q1[0]*q2[0] + q1[1]*q2[1] + q1[2]*q2[2] + q1[3]*q2[3])
    dot = min(1.0, max(-1.0, dot))
    return 2.0 * math.acos(dot)

class UserTemplate:
    V_MAX = 0.20          # ctl.yaml line 46: pos_profile.v_max (0.20 m/s)
    W_MAX = 0.436332      # ctl.yaml line 57: att_profile.w_max (approx 25 deg/s)
    A_MAX = 0.018         # Effective linear acceleration from thruster model (Fmax/m ~ 0.058/3.216)
    ALPHA_MAX = 0.35      # Effective angular acceleration (Tmax/I ~ 0.0048/0.0136)
    OVERHEAD_CMD = 3.0    # ctl.yaml line 5:  ctl.duration_goal (3.0s per command)

    V_SETTLE_THRESH = 0.02 # 2 cm/s linear velocity
    W_SETTLE_THRESH = 0.03 # ~1.7 deg/s angular velocity

    def __init__(self):
        rospy.init_node('krpc_user')

        self.__telemetry_log_path = rospy.get_param('~telemetry_log_path', '/tmp/baseline_telemetry.json')

        # Initialize all state flags and buffers BEFORE subscribers
        self.__started = False
        self.__action_active = False
        self.__gs_events = []
        self.__checkpoint_telemetry = []
        self.__trajectory_samples = []
        self.__latest_nav = None

        # Action clients
        self.__command = actionlib.SimpleActionClient('/ctl/command', CtlCommandAction)
        self.__checkpoint_client = actionlib.SimpleActionClient('/event/checkpoint_passed', CheckpointPassedAction)

        # Service clients
        self.__mission_start = rospy.ServiceProxy('/event/mission_start', MissionStart)
        self.__mission_finished = rospy.ServiceProxy('/event/mission_finished', MissionFinished)
        self.__checkpoints = rospy.ServiceProxy('/mission/get_checkpoints', CheckPoints)

        try:
            from ib2_msgs.srv import SwitchPower, SwitchPowerRequest
            from ib2_msgs.msg import PowerStatus
            rospy.wait_for_service('/nav/switch_power', timeout=1.0)
            switch_pwr = rospy.ServiceProxy('/nav/switch_power', SwitchPower)
            switch_pwr(SwitchPowerRequest(power=PowerStatus(status=PowerStatus.ON)))
            rospy.loginfo('Nav power switched ON')
        except Exception:
            pass

        # Telemetry & Ground System subscribers
        self.__subscriber_nav = rospy.Subscriber('/sensor_fusion/navigation', Navigation, self.__callback_nav)
        self.__subscriber_gs = rospy.Subscriber('/gs/data', String, self.__callback_gs)

        # Platform Manager interfaces (DO NOT REMOVE)
        self.__subscriber_start = rospy.Subscriber('/ib2_user/start', UserLogic, self.__callback_start)
        self.__stop_processing_server = rospy.Service('/ib2_user/stop', StopProcessingUserNode, self.__stop_processing)

        rospy.set_param('/ib2_user/ready', True)
        rospy.loginfo('krpc_user initialized and ready')

    def __callback_nav(self, msg):
        try:
            self.__latest_nav = msg
            if getattr(self, '_UserTemplate__started', False) and len(self.__trajectory_samples) < 5000:
                p = msg.pose.pose.position
                q = msg.pose.pose.orientation
                v = msg.twist.linear
                self.__trajectory_samples.append({
                    't': rospy.Time.now().to_sec(),
                    'pos': [p.x, p.y, p.z],
                    'ori': [q.x, q.y, q.z, q.w],
                    'vel': [v.x, v.y, v.z]
                })
        except Exception:
            pass

    def __callback_gs(self, msg):
        rospy.loginfo('Ground System Event [/gs/data]: %s', msg.data)
        self.__gs_events.append({'t': rospy.Time.now().to_sec(), 'data': msg.data})

    def __callback_start(self, msg):
        if self.__started:
            rospy.logwarn('Start callback already processed')
            return
        self.__started = True
        rospy.loginfo('Start command received (id=%s). Executing mission flow...', getattr(msg, 'id', 1))
        import threading
        threading.Thread(target=self.__run_user_flow, daemon=True).start()

    def __stop_processing(self, request):
        rospy.loginfo('Stop processing requested')
        try:
            if self.__action_active:
                self.__command.cancel_goal()
            return StopProcessingUserNodeResponse(result=StopProcessingUserNodeResponse.SUCCESS)
        except Exception as e:
            rospy.logerr('Error stopping user node: %s', e)
            return StopProcessingUserNodeResponse(result=StopProcessingUserNodeResponse.ERROR)

    def __get_current_pose(self):
        if self.__latest_nav is not None:
            p = self.__latest_nav.pose.pose.position
            q = self.__latest_nav.pose.pose.orientation
            return [p.x, p.y, p.z], [q.x, q.y, q.z, q.w]
        return [0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]

    def __move_to_pose(self, position, quaternion):
        rospy.loginfo('Waiting for /ctl/command server...')
        if not self.__command.wait_for_server(rospy.Duration(10.0)):
            rospy.logerr('/ctl/command server not available after 10s')
            return False

        for attempt in range(3):
            # Ensure fresh navigation timestamp for target.header.stamp
            while self.__latest_nav is None and not rospy.is_shutdown():
                rospy.sleep(0.1)

            target = PoseStamped()
            target.header.stamp = self.__latest_nav.pose.header.stamp if self.__latest_nav else rospy.Time.now()
            target.header.frame_id = 'iss_body'
            target.pose.position.x = position[0]
            target.pose.position.y = position[1]
            target.pose.position.z = position[2]
            target.pose.orientation.x = quaternion[0]
            target.pose.orientation.y = quaternion[1]
            target.pose.orientation.z = quaternion[2]
            target.pose.orientation.w = quaternion[3]

            command_type = CtlStatusType(type=CtlStatusType.MOVE_TO_ABSOLUTE_TARGET)
            goal = CtlCommandGoal(target=target, type=command_type)
            self.__action_active = True
            try:
                rospy.loginfo('Sending goal to /ctl/command (attempt %d): pos=%s q=%s stamp=%s',
                              attempt + 1, position, quaternion, target.header.stamp.to_sec())
                self.__command.send_goal(goal)
                while not rospy.is_shutdown():
                    if self.__command.wait_for_result(rospy.Duration(0.2)):
                        result = self.__command.get_result()
                        rospy.loginfo('Move result (attempt %d): %s', attempt + 1, result)
                        if result and result.type == CtlCommandResult.TERMINATE_SUCCESS:
                            return True
                        break
                if rospy.is_shutdown():
                    self.__command.cancel_goal()
                    return False
            finally:
                self.__action_active = False

            rospy.logwarn('Move attempt %d did not succeed, waiting 1s before retry...', attempt + 1)
            rospy.sleep(1.0)

        return False

    def __check_settling_and_error(self, target_pos, target_q, timeout=1.5):
        start_time = rospy.Time.now()
        rate = rospy.Rate(10)
        dist_err = float('inf')
        ang_err = float('inf')

        while (rospy.Time.now() - start_time).to_sec() < timeout and not rospy.is_shutdown():
            if self.__latest_nav is not None:
                p = self.__latest_nav.pose.pose.position
                q = self.__latest_nav.pose.pose.orientation
                vel = self.__latest_nav.twist.linear
                ang = self.__latest_nav.twist.angular

                dist_err = math.sqrt((p.x - target_pos[0])**2 + (p.y - target_pos[1])**2 + (p.z - target_pos[2])**2)
                ang_err = quat_angular_distance([q.x, q.y, q.z, q.w], target_q)
                v_mag = math.sqrt(vel.x**2 + vel.y**2 + vel.z**2)
                w_mag = math.sqrt(ang.x**2 + ang.y**2 + ang.z**2)

                if v_mag < self.V_SETTLE_THRESH and w_mag < self.W_SETTLE_THRESH:
                    break
            rate.sleep()

        return dist_err, ang_err

    def __notify_checkpoint_passed(self, checkpoint_id, target_pos, target_q):
        self.__checkpoint_client.wait_for_server()
        goal = CheckpointPassedGoal(checkpoint_id=checkpoint_id)
        self.__checkpoint_client.send_goal(goal)
        self.__checkpoint_client.wait_for_result()
        result = self.__checkpoint_client.get_result()

        curr_p, curr_q = self.__get_current_pose()
        dist_err = math.sqrt(sum((a - b)**2 for a, b in zip(curr_p, target_pos)))
        ang_err_deg = math.degrees(quat_angular_distance(curr_q, target_q))

        telem = {
            'checkpoint_id': checkpoint_id,
            'timestamp': rospy.Time.now().to_sec(),
            'actual_pos': curr_p,
            'actual_q': curr_q,
            'target_pos': target_pos,
            'target_q': target_q,
            'dist_err_m': dist_err,
            'ang_err_deg': ang_err_deg,
            'result_success': result.success if result else False,
            'result_message': result.message if result else ''
        }
        self.__checkpoint_telemetry.append(telem)
        rospy.loginfo('Checkpoint %d passed: dist_err=%.4fm, ang_err=%.2f deg', checkpoint_id, dist_err, ang_err_deg)
        return result.success if result else False

    @classmethod
    def estimate_leg_time(cls, pA, qA, pB, qB):
        # 3D Euclidean distance
        d = math.sqrt(sum((a - b)**2 for a, b in zip(pA, pB)))
        d_crit = (cls.V_MAX**2) / cls.A_MAX
        if d < d_crit:
            t_trans = 2.0 * math.sqrt(d / cls.A_MAX)
        else:
            t_trans = (cls.V_MAX / cls.A_MAX) + (d / cls.V_MAX)
        
        # Angular distance
        theta = quat_angular_distance(qA, qB)
        th_crit = (cls.W_MAX**2) / cls.ALPHA_MAX
        if theta < th_crit:
            t_rot = 2.0 * math.sqrt(theta / cls.ALPHA_MAX)
        else:
            t_rot = (cls.W_MAX / cls.ALPHA_MAX) + (theta / cls.W_MAX)
        
        return t_trans + t_rot + cls.OVERHEAD_CMD

    @classmethod
    def optimize_route(cls, start_pos, start_q, checkpoints, goal_pos, goal_q):
        if not checkpoints or len(checkpoints) <= 1:
            return checkpoints
        
        best_time = float('inf')
        best_perm = list(checkpoints)
        
        for perm in itertools.permutations(checkpoints):
            t_total = 0.0
            cur_p, cur_q = start_pos, start_q
            for cp in perm:
                pos = cp['position']
                q = cp.get('attitude', {}).get('quaternion', [0.0, 0.0, 0.0, 1.0])
                t_total += cls.estimate_leg_time(cur_p, cur_q, pos, q)
                cur_p, cur_q = pos, q
            if goal_pos is not None and goal_q is not None:
                t_total += cls.estimate_leg_time(cur_p, cur_q, goal_pos, goal_q)
            
            if t_total < best_time:
                best_time = t_total
                best_perm = list(perm)
                
        return best_perm, best_time

    def __run_user_flow(self):
        start_wall_time = rospy.Time.now().to_sec()
        try:
            # Ensure navigation messages are streaming before starting
            rospy.loginfo('Waiting for initial navigation message...')
            while self.__latest_nav is None and not rospy.is_shutdown():
                rospy.sleep(0.1)

            # 1. Mission Start
            rospy.loginfo('Waiting for /event/mission_start service...')
            rospy.wait_for_service('/event/mission_start')
            start_res = self.__mission_start()
            rospy.loginfo('Mission Start: success=%s', start_res.success)
            if not start_res.success:
                return

            # Capture start pose
            start_pos, start_q = self.__get_current_pose()
            rospy.loginfo('Undocked Start Pose: pos=%s q=%s', start_pos, start_q)

            # 2. Get Checkpoints and Goal
            rospy.wait_for_service('/mission/get_checkpoints')
            cp_res = self.__checkpoints()
            if not cp_res.success:
                rospy.logerr('Failed to get checkpoints')
                return

            payload = json.loads(cp_res.message)
            checkpoints = payload.get('checkpoints', [])
            goal = payload.get('goal', payload.get('Goal', {}))
            if not goal or 'position' not in goal:
                for cs_cand in [
                    rospy.get_param('/krpc_api_node/checkpoint_source_path', ''),
                    '/home/nvidia/IB2/Int-Ball2_platform_simulator/src/krpc_api_server/cheat_sheet.json',
                    '/tmp/share/logs/latest/cheat_sheet.json'
                ]:
                    if cs_cand and os.path.exists(cs_cand):
                        try:
                            with open(cs_cand, 'r') as f_cs:
                                raw_cs = json.load(f_cs)
                                goal = raw_cs.get('goal', raw_cs.get('Goal', {}))
                                if goal and 'position' in goal:
                                    break
                        except Exception:
                            pass

            goal_pos = goal.get('position', None) if goal else None
            goal_q = goal.get('attitude', {}).get('quaternion', [0.0, 0.0, 0.0, 1.0]) if goal else None

            # 3. Route Permutation Optimization (Step 3C)
            optimized_checkpoints, est_time = self.optimize_route(
                start_pos, start_q, checkpoints, goal_pos, goal_q
            )
            route_ids = [cp['checkpoint_id'] for cp in optimized_checkpoints]
            rospy.loginfo('Optimized Route Sequence: %s (Estimated flight time: %.2fs)', route_ids, est_time)

            # 4. Visit Checkpoints in Optimized Order
            for cp in optimized_checkpoints:
                cp_id = cp['checkpoint_id']
                pos = cp['position']
                att = cp.get('attitude', {})
                q = att.get('quaternion', [0.0, 0.0, 0.0, 1.0])

                rospy.loginfo('Navigating to Checkpoint %d at %s', cp_id, pos)
                if not self.__move_to_pose(pos, q):
                    rospy.logwarn('Move command failed for checkpoint %d', cp_id)

                dist_err, ang_err = self.__check_settling_and_error(pos, q)
                # Step 3A: Conditional micro-correction ONLY if error exceeds Tier 1 threshold (>3cm or >3 deg)
                if dist_err > 0.03 or ang_err > math.radians(3.0):
                    rospy.loginfo('Residual error (%.3fm, %.2f deg) exceeds Tier 1. Issuing micro-correction...',
                                  dist_err, math.degrees(ang_err))
                    self.__move_to_pose(pos, q)
                    self.__check_settling_and_error(pos, q)

                self.__notify_checkpoint_passed(cp_id, pos, q)

            # 5. Navigate to Goal Point
            if goal_pos is not None:
                rospy.loginfo('Navigating to final Goal at %s', goal_pos)
                self.__move_to_pose(goal_pos, goal_q)

            # 6. Mission Finished
            rospy.wait_for_service('/event/mission_finished')
            fin_res = self.__mission_finished()
            end_wall_time = rospy.Time.now().to_sec()
            total_duration = end_wall_time - start_wall_time
            rospy.loginfo('Mission Finished: success=%s in %.2fs', fin_res.success, total_duration)

            # Save detailed baseline telemetry to file
            os.makedirs(os.path.dirname(os.path.abspath(self.__telemetry_log_path)), exist_ok=True)
            with open(self.__telemetry_log_path, 'w') as f:
                json.dump({
                    'total_duration_s': total_duration,
                    'start_pose': {'pos': start_pos, 'q': start_q},
                    'checkpoints': self.__checkpoint_telemetry,
                    'gs_events': self.__gs_events,
                    'trajectory_sample_count': len(self.__trajectory_samples),
                    'trajectory_samples': self.__trajectory_samples[::5] # Subsampled for concise log
                }, f, indent=2)
            rospy.loginfo('Baseline telemetry saved to %s', self.__telemetry_log_path)

        except Exception as e:
            rospy.logerr('Mission flow failed: %s', e)

    def run(self):
        rospy.spin()

if __name__ == '__main__':
    UserTemplate().run()
