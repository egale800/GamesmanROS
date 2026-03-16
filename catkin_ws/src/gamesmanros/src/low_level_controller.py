#!/usr/bin/env python3
import sys
import rospy
import moveit_commander
import geometry_msgs.msg
from moveit_commander.conversions import pose_to_list
from tf.transformations import quaternion_from_euler
import time
from mycobot_communication.msg import MycobotGripperStatus
from math import pi

# Initialize MoveIt and ROS nodes
moveit_commander.roscpp_initialize(sys.argv)
# rospy.init_node("moveit_trajectory_planner", anonymous=True)

# Initialize robot commander and scene interface
robot = moveit_commander.RobotCommander()
# scene = moveit_commander.PlanningSceneInterface()

# Initialize MoveGroupCommander for your arm
group_name = "arm_group"  # Ensure this matches your MoveIt configuration
move_group = moveit_commander.MoveGroupCommander(group_name)

# Tolerances - relaxed slightly to improve IK success rate across all board positions
move_group.set_goal_position_tolerance(0.01)       # 1 cm
move_group.set_goal_orientation_tolerance(0.05)    # ~3 degrees

gripper = rospy.Publisher("/mycobot/gripper_status", MycobotGripperStatus, queue_size=10)


def plan_to_xyz(x, y, z):
    current_state = robot.get_current_state()
    move_group.set_start_state(current_state)

    # Set up a Pose target at the desired location
    pose_goal = geometry_msgs.msg.Pose()
    pose_goal.position.x = x
    pose_goal.position.y = y
    pose_goal.position.z = z

    # Pure straight-down orientation (180° around X only).
    # The previous code also applied a 45° Z rotation and ~11° X tilt which
    # caused NO_IK_SOLUTION failures for board positions outside dodgem's range.
    # If the gripper physically needs a Z rotation due to mounting, re-add it here.
    q = quaternion_from_euler(pi, 0, 0)

    pose_goal.orientation.x = round(q[0], 6)
    pose_goal.orientation.y = round(q[1], 6)
    pose_goal.orientation.z = round(q[2], 6)
    pose_goal.orientation.w = round(q[3], 6)

    move_group.set_pose_target(pose_goal)

    # Try LIN first (straight-line cartesian path), fall back to PTP if it fails.
    # LIN requires a valid IK at every interpolated point along the path, so it
    # fails more often than PTP for poses near the edge of the workspace.
    move_group.set_planner_id("LIN")
    plan = move_group.plan()

    if not plan[0]:
        rospy.logwarn("LIN planning failed, retrying with PTP planner...")
        move_group.set_planner_id("PTP")
        plan = move_group.plan()

    if not plan[0]:
        rospy.logwarn("Planning failed for target pose: x=%.4f y=%.4f z=%.4f" % (x, y, z))
        return False

    move_group.execute(plan[1], wait=True)
    rospy.loginfo("Trajectory executed successfully.")
    return True


def gripper_status(state):
    gripper_states = {"open": 1, "close": 0}
    msg = MycobotGripperStatus()
    msg.Status = gripper_states[state]
    # Publish multiple times with sleeps to ensure the gripper receives the command
    for _ in range(2):
        gripper.publish(msg)
    time.sleep(1)
    for _ in range(2):
        gripper.publish(msg)
    time.sleep(1)
    for _ in range(7):
        gripper.publish(msg)