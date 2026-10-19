#!/bin/bash

CHECKPOINT_SOURCE_PATH=/tmp/share/logs/latest/cheat_sheet.json

source /opt/ros/melodic/setup.bash
source /users/catkin_ws/devel/setup.bash

# Wait the simulator to be ready
while [ "$(rosparam get /krpc/ready 2>&1)" != "true" ];
do
    sleep 2;
done

if [ ! -f ${CHECKPOINT_SOURCE_PATH} ]; then
    echo "checkpoint source file not found: ${CHECKPOINT_SOURCE_PATH}" >&2
    exit 1
fi

USER_LOG_DIR=${ROS_LOG_DIR:-${HOME}/.ros/log}
USER_CONSOLE_LOG=${USER_LOG_DIR}/krpc_user_console.log
mkdir -p ${USER_LOG_DIR}
: > ${USER_CONSOLE_LOG}

# Tag ROS log lines with the node name (works for both rospy and roscpp) so that
# run.sh can extract /krpc_user output into user_program_output.log.
export ROSCONSOLE_FORMAT='[${severity}] [${node}] [${time}]: ${message}'
export PYTHONUNBUFFERED=1

echo "Launch unified KRPC (API + user)"
bash $(dirname $0)/tail_log.sh ${USER_CONSOLE_LOG} &

# stdbuf: keep C/C++ node stdout line-buffered so logs survive abrupt termination.
stdbuf -oL -eL roslaunch krpc_user krpc_user.launch checkpoint_source_path:=${CHECKPOINT_SOURCE_PATH} > ${USER_CONSOLE_LOG} 2>&1
exit $?
