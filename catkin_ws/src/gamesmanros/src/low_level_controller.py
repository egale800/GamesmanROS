#!/usr/bin/env python3
import sys
import rospy
import moveit_commander
import geometry_msgs.msg
from tf.transformations import quaternion_from_euler, quaternion_multiply
import time
from mycobot_communication.msg import MycobotGripperStatus
from math import pi

# Initialize MoveIt and ROS nodes
moveit_commander.roscpp_initialize(sys.argv)

# Initialize robot commander and MoveGroup
robot = moveit_commander.RobotCommander()
group_name = "arm_group"
move_group = moveit_commander.MoveGroupCommander(group_name)
move_group.set_planner_id("LIN")

gripper = rospy.Publisher("/mycobot/gripper_status", MycobotGripperStatus, queue_size=10)


def get_fixed_orientation():
    """
    Start simple: tool-down orientation only.
    Once this works, you can add yaw/tilt back in.
    """
    q = quaternion_from_euler(pi, 0, 0)
    return q

    # Later, if needed, try this again:
    # q1 = quaternion_from_euler(pi, 0, 0)       # tool down
    # q2 = quaternion_from_euler(0, 0, pi/4)     # yaw
    # q3 = quaternion_from_euler(-pi/16, 0, 0)   # slight tilt
    # q12 = quaternion_multiply(q1, q2)
    # q = quaternion_multiply(q12, q3)
    # return q


def plan_to_xyz(x, y, z):
    # Always start from a clean planning state
    move_group.stop()
    move_group.clear_pose_targets()
    move_group.clear_path_constraints()
    move_group.set_start_state_to_current_state()

    # Build a fresh pose target
    pose_goal = geometry_msgs.msg.Pose()
    pose_goal.position.x = x
    pose_goal.position.y = y
    pose_goal.position.z = z

    q = get_fixed_orientation()
    pose_goal.orientation.x = q[0]
    pose_goal.orientation.y = q[1]
    pose_goal.orientation.z = q[2]
    pose_goal.orientation.w = q[3]

    rospy.loginfo(
        f"Planning to x={x:.4f}, y={y:.4f}, z={z:.4f}, "
        f"quat=({q[0]:.4f}, {q[1]:.4f}, {q[2]:.4f}, {q[3]:.4f})"
    )

    # Set ONLY one pose target
    move_group.set_pose_target(pose_goal)

    # Plan
    plan_result = move_group.plan()

    # Handle MoveIt return format differences
    if isinstance(plan_result, tuple):
        success, traj, planning_time, error_code = plan_result
    else:
        success = True
        traj = plan_result

    if not success or traj is None:
        rospy.logwarn("Planning failed for the target pose.")
        move_group.clear_pose_targets()
        return False

    # Execute
    executed = move_group.execute(traj, wait=True)
    move_group.stop()
    move_group.clear_pose_targets()

    if not executed:
        rospy.logwarn("Execution failed.")
        return False

    rospy.loginfo("Trajectory executed successfully.")
    return True


def gripper_status(state):
    gripper_states = {"open": 1, "close": 0}
    msg = MycobotGripperStatus()
    msg.Status = gripper_states[state]

    # Keep your repeated publish behavior for now
    for _ in range(2):
        gripper.publish(msg)
    time.sleep(1)

    for _ in range(2):
        gripper.publish(msg)
    time.sleep(1)

    for _ in range(7):
        gripper.publish(msg)