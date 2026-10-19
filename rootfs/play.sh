#!/bin/bash

## Log label ------------------------------------------------------
LABEL_INFO="[INFO]"
LABEL_WARN="[WARN]"
LABEL_ERROR="[ERROR]"
LABEL_DEBUG="[DEBUG]"

## Local paths ----------------------------------------------------
USERNAME=intball
BUILD_PATH=/home/${USERNAME}/catkin_ws/
WORK_DIR=/tmp

logging() {
    # $1:log level
    # $2:log message

    if [ $1 = ${LABEL_DEBUG} ] && [ ! -z ${DEBUG} ]; then
        echo '=================================================================================='
        echo `date '+%Y/%m/%d-%H:%M:%S'` $1 "$2" | tee -a ${GAME_LOG}
        echo '=================================================================================='
    else
        echo `date '+%Y/%m/%d-%H:%M:%S'` $1 "$2" | tee -a ${GAME_LOG}
    fi
}

logging_wait(){
    # $1:label
    # $2:sleep time

    logging $LABEL_INFO "Waiting ""$1"" "$2"..."
    sleep $2
    logging $LABEL_INFO "Waiting ""$1"" done."
}

set_env(){
    # Set to disable buffered to write logs.
    export PYTHONUNBUFFERED=1
    export ROSCONSOLE_STDOUT_LINE_BUFFERED=1
}

reproduce_random_env() {
    cp /tmp/share/logs/latest/textures/*   ~/catkin_ws/src/platform_sim/krpc_description/description/media/ib2_iss/media/materials/textures/
    cp /tmp/share/logs/latest/iss.urdf ~/catkin_ws/src/platform_sim/description/urdf/
}

start_replay() {
    export DISPLAY=":1"
    source /opt/ros/melodic/setup.bash
    source $BUILD_PATH/devel/setup.bash

    logging $LABEL_INFO "Building up ISS Kibo..."
    roslaunch description description.launch &

    sleep 10

    RATE=${PLAY_RATE:-1.0}
    START=${START_TIME:-0}
    logging $LABEL_INFO "Start rosbag play from ${START}s with play rate ${RATE}"
    rosbag play -r ${RATE} -s ${START} /tmp/share/logs/latest/simulation.bag
}

main() {
    logging $LABEL_INFO "Start replay."

    set_env && \
    reproduce_random_env && \
    start_replay &&

    logging $LABEL_INFO "End replay."

    exit 0
}

main
