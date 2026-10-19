#!/bin/bash

# Const -----------------------------------------------------------
## Sleep period ---------------------------------------------------
WAIT_VNC=5s
WAIT_JUDGE=1s
WAIT_LAUNCH_SIM=30s
WAIT_TERMINATE_SIM=10s

## Log label ------------------------------------------------------
LABEL_INFO="[INFO]"
LABEL_WARN="[WARN]"
LABEL_ERROR="[ERROR]"
LABEL_DEBUG="[DEBUG]"

## Local paths ----------------------------------------------------
USERNAME=intball
BUILD_PATH=/home/${USERNAME}/catkin_ws/
PYTHON3_OVERLAY_PATH=/home/${USERNAME}/ros_python3_ws
WORK_DIR=/tmp

## Modules --------------------------------------------------------
RANDOM_ENV_GENERATOR=/krpc/random_env_generator/generate_objects.py
JUDGE_MODULE=/krpc/judge_module/judge.py
STATUS_INDICATOR_MODULE=/krpc/status_indicator_module/krpc_status_indicator.py
FLIGHT_RECORDER_MODULE=/krpc/flight_recorder_module/krpc_flight_recorder.py

## Feature flags --------------------------------------------------
ENABLE_STATUS_INDICATOR=${ENABLE_STATUS_INDICATOR:-true}
ENABLE_FLIGHT_RECORDER=${ENABLE_FLIGHT_RECORDER:-true}
ENABLE_DEBUG_MODE=${ENABLE_DEBUG_MODE:-false}
LEVELS=${LEVELS:-normal}
SIM_MODE=${SIM_MODE:-regular}

case "${SIM_MODE}" in
    regular|beginners)
        ;;
    *)
        echo "[ERROR] Invalid SIM_MODE=${SIM_MODE}. Expected regular or beginners." >&2
        exit 1
        ;;
esac
    export SIM_MODE

## Input ----------------------------------------------------------
CHEAT_SHEET_LATEST=/tmp/share/logs/latest/cheat_sheet.json
CHEAT_SHEET_LOG=
RANDOM_ENV_OUTPUT_DIR=${WORK_DIR}/random_env/${ROUND:-simulation}

## Output ---------------------------------------------------------
RESULT_JSON=${WORK_DIR}/result.json
ROSBAG=${WORK_DIR}/simulation.bag

## Log files ------------------------------------------------------
GAME_LOG=${WORK_DIR}/game.log
JUDGE_LOG=${WORK_DIR}/judge.log
SYSTEM_LOG=${WORK_DIR}/system.log
ROSBAG_LOG=${WORK_DIR}/rosbag.log
FINISH_REPORT=${WORK_DIR}/finish_report
STATUS_INDICATOR_LOG=${WORK_DIR}/status_indicator.log
FLIGHT_RECORDER_LOG=${WORK_DIR}/flight_recorder.log

# Functions -------------------------------------------------------
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

is_enabled() {
    case "${1}" in
        1|true|TRUE|yes|YES|on|ON)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Poll until the gazebo_ros services are registered, instead of relying on a fixed sleep.
# This avoids "An instance of Gazebo is not running." races on slower (e.g. EC2) instances.
wait_for_gazebo_ready(){
    local timeout=${1:-60}
    local waited=0
    logging $LABEL_INFO "Waiting for Gazebo server to be ready (timeout=${timeout}s)..."
    until rosservice list 2>/dev/null | grep -q '^/gazebo/pause_physics$'; do
        if [ ${waited} -ge ${timeout} ]; then
            logging $LABEL_ERROR "Gazebo server did not become ready within ${timeout}s"
            return 1
        fi
        sleep 1
        waited=$((waited + 1))
    done
    logging $LABEL_INFO "Gazebo server is ready (waited ${waited}s)"
    return 0
}

wait_for_iss_model(){
    local timeout=${1:-60}
    local waited=0
    logging $LABEL_INFO "Waiting for ISS model to be spawned (timeout=${timeout}s)..."
    until rosservice call /gazebo/get_model_state "model_name: 'iss'" 2>/dev/null | grep -q 'success: True'; do
        if [ ${waited} -ge ${timeout} ]; then
            logging $LABEL_ERROR "ISS model was not spawned within ${timeout}s"
            return 1
        fi
        sleep 1
        waited=$((waited + 1))
    done
    logging $LABEL_INFO "ISS model is ready (waited ${waited}s)"
    return 0
}

wait_for_rviz_iss_ready(){
    local timeout=${1:-30}
    local waited=0
    logging $LABEL_INFO "Waiting for RViz ISS display inputs (timeout=${timeout}s)..."
    until rosnode list 2>/dev/null | grep -q '^/rviz$' && \
          rosnode list 2>/dev/null | grep -q '^/iss_state_publisher$' && \
            rosparam get /iss_description >/dev/null 2>&1; do
        if [ ${waited} -ge ${timeout} ]; then
            logging $LABEL_ERROR "RViz ISS display inputs were not ready within ${timeout}s"
            rosnode list &>> ${SYSTEM_LOG} || true
            rosparam get /iss_description &>> ${SYSTEM_LOG} || true
            return 1
        fi
        sleep 1
        waited=$((waited + 1))
    done
    logging $LABEL_INFO "RViz ISS display inputs are ready (waited ${waited}s)"
    timeout 3 rosrun tf tf_echo base iss_body &>> ${SYSTEM_LOG} || \
        logging $LABEL_WARN "base -> iss_body TF was not confirmed yet; continuing because RViz and URDF are ready."
    return 0
}

# Retry wrapper for "gz world -p 0" since a cold/slow Gazebo boot can make the first call fail.
gz_unpause(){
    local retries=5
    local i=0
    until gz world -p 0 &>>${SYSTEM_LOG}; do
        i=$((i + 1))
        if [ ${i} -ge ${retries} ]; then
            logging $LABEL_ERROR "gz world -p 0 failed after ${retries} attempts"
            return 1
        fi
        logging $LABEL_WARN "gz world -p 0 failed, retrying (${i}/${retries})..."
        sleep 2
    done
    return 0
}

set_timestamp(){
    logging $LABEL_INFO "Setting simulation timestamp starts..."
    export SIMULATION_TIMESTAMP=$(date '+%Y%m%d%H%M%S')
    export LOG_ROOT_DIR=/tmp/share/logs
    export CHEAT_SHEET_LOG=${LOG_ROOT_DIR}/${SIMULATION_TIMESTAMP}/cheat_sheet.json
    export TIMESTAMP_FILE=${WORK_DIR}/simulation_timestamp
    mkdir -p ${LOG_ROOT_DIR}/${SIMULATION_TIMESTAMP}
    echo ${SIMULATION_TIMESTAMP} > ${TIMESTAMP_FILE}
    # Clear previous run's ROS logs so roslaunch doesn't keep accumulating UUID dirs across runs.
    rm -rf ${LOG_ROOT_DIR}/latest/user_programs_logs
    logging $LABEL_INFO "Simulation timestamp: ${SIMULATION_TIMESTAMP}"
    logging $LABEL_INFO "Simulation logs dir: ${LOG_ROOT_DIR}/${SIMULATION_TIMESTAMP}"
    logging $LABEL_INFO "Setting simulation timestamp has done."
}

set_random_env(){
    logging $LABEL_INFO "Setting random env starts..."
    cd `dirname ${RANDOM_ENV_GENERATOR}`
    rm -rf ${RANDOM_ENV_OUTPUT_DIR}
    mkdir -p ${RANDOM_ENV_OUTPUT_DIR}

    # Generate randomized checkpoint data for this simulation run.
    if ! python3 `basename ${RANDOM_ENV_GENERATOR}` -l ${LEVELS} -o ${RANDOM_ENV_OUTPUT_DIR} &>> ${SYSTEM_LOG}; then
        logging $LABEL_ERROR "cheat_sheet generation failed; see ${SYSTEM_LOG}"
        return 1
    fi

    CHEAT_SHEET_TEMP=${RANDOM_ENV_OUTPUT_DIR}/cheat_sheet_01.json

    if [ ! -f ${CHEAT_SHEET_TEMP} ]; then
        logging $LABEL_ERROR "cheat_sheet not found: ${CHEAT_SHEET_TEMP}"
        tail -20 ${SYSTEM_LOG} >> ${GAME_LOG}
        return 1
    else
        # Save cheat_sheet for this run and update latest reference for runtime consumers.
        cp ${CHEAT_SHEET_TEMP} ${CHEAT_SHEET_LOG}

        if [ ! -f ${CHEAT_SHEET_LOG} ]; then
            logging $LABEL_ERROR "Failed to copy cheat_sheet_01.json to ${CHEAT_SHEET_LOG}"
        else
            logging $LABEL_INFO "cheat_sheet.json created at: ${CHEAT_SHEET_LOG}"
            mkdir -p ${LOG_ROOT_DIR}/latest
            cp ${CHEAT_SHEET_LOG} ${CHEAT_SHEET_LATEST}
            logging $LABEL_INFO "cheat_sheet.json updated at: ${CHEAT_SHEET_LATEST}"
        fi
    fi

    # Create local copy for consistency
    if [ -f ${CHEAT_SHEET_LATEST} ]; then
        cp ${CHEAT_SHEET_LATEST} ${WORK_DIR}/cheat_sheet_out.json
    fi

    logging $LABEL_INFO "Simulation model assets were prepared during Docker image build."

    if [ ! -z ${DEBUG} ]; then
        logging $LABEL_DEBUG "CHEAT SHEET"
        cat ${CHEAT_SHEET_LATEST}
        echo
    fi

    cd - &> /dev/null
    logging $LABEL_INFO "Setting random env has done."
}

launch_simulation(){
    logging $LABEL_INFO "Launching simulation starts..."
    export DISPLAY=":1"

    # Wait for Xvfb to be ready (max 30s)
    for i in $(seq 1 30); do
        xdpyinfo -display :1 &>/dev/null && break
        sleep 1
    done
    if ! xdpyinfo -display :1 &>/dev/null; then
        logging $LABEL_ERROR "DISPLAY :1 not available after 30s"
    fi

    source /opt/ros/melodic/setup.bash
    source $BUILD_PATH/devel/setup.bash
    # Start Gazebo first. RViz is launched after the ISS model exists so it can
    # read iss_description before the anti-cheat cleanup below removes it.
    roslaunch ib2_gazebo sim.launch gui:=false rviz:=false &>> ${SYSTEM_LOG} &

    wait_for_gazebo_ready 60
    wait_for_iss_model 60
    roslaunch description description.launch &>> ${SYSTEM_LOG} &
    RVIZ_ISS_READY=false
    if wait_for_rviz_iss_ready 30; then
        RVIZ_ISS_READY=true
    else
        logging $LABEL_WARN "Keep /iss_description because RViz ISS inputs were not confirmed."
    fi
    logging_wait "LAUNCH SIM" ${WAIT_LAUNCH_SIM}

    # distribute compressed images
    rosrun image_transport republish raw in:=/camera_main/image_raw compressed out:=/camera_main/image_raw/compressed &
    rosrun image_transport republish raw in:=/camera_left/image_raw compressed out:=/camera_left/image_raw/compressed &
    rosrun image_transport republish raw in:=/camera_right/image_raw compressed out:=/camera_right/image_raw/compressed &

    rosservice call /nav/switch_power \
        "power:
            status: 1" &>> ${SYSTEM_LOG}
    roslaunch ctl_only bringup.launch &>> ${SYSTEM_LOG} &
    roslaunch fsm bringup.launch &>> ${SYSTEM_LOG} &
    # delete urdf from rosparam to prevent hacking after RViz has read it
    if [ "${RVIZ_ISS_READY}" = "true" ]; then
        rosparam delete /iss_description
    fi
    logging $LABEL_INFO "Launching simulation has done."
}

launch_record_rosbag(){
    logging $LABEL_INFO "Launching recording rosbag starts..."
    rosbag record \
            -a -q --bz2 \
            --output-name=${ROSBAG} \
            --buffsize=4096 \
            --exclude='(.*)airflow(.*)' \
            __name:=record_rosbag &>> ${ROSBAG_LOG} &
    logging $LABEL_INFO "Launching recording rosbag has done."
}

launch_judge_module(){
    logging $LABEL_INFO "Launching judge module starts..."
    (
        source "${PYTHON3_OVERLAY_PATH}/devel/setup.bash"
        cd "$(dirname "${JUDGE_MODULE}")"
        exec python3 "$(basename "${JUDGE_MODULE}")" \
            -c "${CHEAT_SHEET_LATEST}" \
            -o "${WORK_DIR}" \
            -f "${RESULT_JSON}" \
            -i "${FINISH_REPORT}"
    ) &> "${JUDGE_LOG}" &

    logging_wait "JUDGE" ${WAIT_JUDGE}

    logging $LABEL_INFO "Launching judge module has done."
}

launch_status_indicator_module(){
    if ! is_enabled "${ENABLE_STATUS_INDICATOR}"; then
        logging $LABEL_INFO "Status indicator is disabled by feature flag."
        return 0
    fi

    if [ ! -f ${STATUS_INDICATOR_MODULE} ]; then
        logging $LABEL_WARN "Status indicator module not found: ${STATUS_INDICATOR_MODULE}"
        return 0
    fi

    if ! rospack find jsk_rviz_plugins &> /dev/null; then
        logging $LABEL_WARN "jsk_rviz_plugins is unavailable; skip status indicator startup."
        return 0
    fi

    logging $LABEL_INFO "Launching status indicator module starts..."
    local status_indicator_args=(-c "${CHEAT_SHEET_LATEST}")
    if is_enabled "${ENABLE_DEBUG_MODE}"; then
        logging $LABEL_INFO "Debug mode is enabled: self position overlay will be shown."
        status_indicator_args+=(--debug)
    fi
    python3 ${STATUS_INDICATOR_MODULE} "${status_indicator_args[@]}" &> ${STATUS_INDICATOR_LOG} &
    logging $LABEL_INFO "Launching status indicator module has done."
}

launch_flight_recorder_module(){
    if ! is_enabled "${ENABLE_FLIGHT_RECORDER}"; then
        logging $LABEL_INFO "Flight recorder is disabled by feature flag."
        return 0
    fi

    if [ ! -f ${FLIGHT_RECORDER_MODULE} ]; then
        logging $LABEL_WARN "Flight recorder module not found: ${FLIGHT_RECORDER_MODULE}"
        return 0
    fi

    logging $LABEL_INFO "Launching flight recorder module starts..."
    python3 ${FLIGHT_RECORDER_MODULE} -o /tmp/share/logs/latest/data.json -l ${HOME}/ib2.log &> ${FLIGHT_RECORDER_LOG} &
    logging $LABEL_INFO "Launching flight recorder module has done."
}

watch_dog(){
    logging $LABEL_INFO "Watchdog starts..."
    # reserve shutdown
    # 120m -> 120
    playTimeSec=$((${playTime:0:-1}*60))
    logging $LABEL_INFO "Instance will be shutdown after ${playTimeSec} secs"

    timer=0
    continue=True

    # while timer < playTimeSec
    while [ ${timer} -lt ${playTimeSec} ]
    do
        if [ -e ${FINISH_REPORT} ]; then
            break
        fi
        sleep 1s
        ((timer+=1))
    done

    logging $LABEL_INFO "Watchdog has done."
}

catch_error(){
    logging $LABEL_ERROR "Some error occured, STOPPED."
}

force_exit(){
    source /opt/ros/melodic/setup.bash
    rosnode kill /record_rosbag &>> ${SYSTEM_LOG} || true
    killall roslaunch &>> ${SYSTEM_LOG} || true
    logging_wait "TERMINATE SIM" ${WAIT_TERMINATE_SIM}
}

extract_user_program_output_log(){
    local ros_log_dir=${1}
    local output_log=${2}
    local console_log=${ros_log_dir}/krpc_user_console.log

    mkdir -p "$(dirname "${output_log}")"
    : > "${output_log}"

    if [ ! -f "${console_log}" ]; then
        logging $LABEL_WARN "User console log not found: ${console_log}"
        return 0
    fi

    # console_log is roslaunch screen output with ROSCONSOLE_FORMAT set in boot-ib2.sh.
    python3 - "${console_log}" "${output_log}" <<'EOF'
import datetime
import re
import sys

USER_NODE = '/krpc_user'
ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
ros_line = re.compile(r'^\[\s*([A-Z]+)\] \[([^\]]*)\] \[([0-9.]+)(?:, [0-9.]+)?\]: ?(.*)$')
proc_line = re.compile(r'^\[([A-Za-z0-9_]+)-[0-9]+\] ')
roslaunch_noise = re.compile(r'^(process\[|log file: |all processes on machine|shutting down processing monitor|\.\.\. shutting down|done$)')

started = False
keep = True
with open(sys.argv[1], errors='replace') as src, open(sys.argv[2], 'w') as dst:
    for line in src:
        line = ansi_escape.sub('', line.rstrip('\n'))
        if not started:
            started = line.startswith('process[krpc_user-')
            continue
        m = ros_line.match(line)
        if m:
            keep = m.group(2) == USER_NODE
            if keep:
                t = datetime.datetime.fromtimestamp(float(m.group(3)))
                dst.write('[rosout][%s] %s,%03d: %s\n' % (
                    m.group(1), t.strftime('%Y-%m-%d %H:%M:%S'), t.microsecond // 1000, m.group(4)))
            continue
        m = proc_line.match(line)
        if m:
            keep = m.group(1) == 'krpc_user'
            if keep:
                dst.write(line + '\n')
            continue
        if roslaunch_noise.match(line):
            continue
        # Untagged lines: print()/std::cout output or continuation of a multi-line log message.
        if keep:
            dst.write(line + '\n')
EOF
}

save_logs() {
    LOG_ROOT_DIR=/tmp/share/logs
    LATEST_DIR=${LOG_ROOT_DIR}/latest
    DIR_NAME=${SIMULATION_TIMESTAMP}
    TIMESTAMP_FILE=${WORK_DIR}/simulation_timestamp
    DEST_DIR=${LOG_ROOT_DIR}/${DIR_NAME}
    JUDGE_DEST_DIR=${DEST_DIR}/judge_module
    FLIGHT_RECORDER_DEST_DIR=${DEST_DIR}/flight_recorder_logs
    TEXTURES_DIR=/home/${USERNAME}/catkin_ws/src/platform_sim/krpc_description/description/media/ib2_iss/media/materials/textures
    ISS_URDF=/home/${USERNAME}/catkin_ws/src/platform_sim/description/urdf/iss.urdf
    JUDGE_WORK_DIR=${WORK_DIR}

    # Recover timestamp from file when env var is lost.
    if [ -z "${DIR_NAME}" ] && [ -e ${TIMESTAMP_FILE} ]; then
        DIR_NAME=$(cat ${TIMESTAMP_FILE})
        DEST_DIR=${LOG_ROOT_DIR}/${DIR_NAME}
        logging $LABEL_WARN "SIMULATION_TIMESTAMP is empty. Recovered from ${TIMESTAMP_FILE}: ${DIR_NAME}"
    fi

    # Last resort: recover from CHEAT_SHEET_LOG only when dirname looks like timestamp (14 digits).
    if [ -z "${DIR_NAME}" ] && [ ! -z "${CHEAT_SHEET_LOG}" ]; then
        CANDIDATE_DIR=$(basename "$(dirname "${CHEAT_SHEET_LOG}")")
        if [[ ${CANDIDATE_DIR} =~ ^[0-9]{14}$ ]]; then
            DIR_NAME=${CANDIDATE_DIR}
            DEST_DIR=${LOG_ROOT_DIR}/${DIR_NAME}
            logging $LABEL_WARN "Recovered timestamp from CHEAT_SHEET_LOG path: ${DIR_NAME}"
        else
            logging $LABEL_WARN "CHEAT_SHEET_LOG dirname is not timestamp: ${CANDIDATE_DIR}"
        fi
    fi

    if [ -z "${DIR_NAME}" ]; then
        logging $LABEL_ERROR "save_logs skipped: SIMULATION_TIMESTAMP is empty (CHEAT_SHEET_LOG=${CHEAT_SHEET_LOG})"
        return 1
    fi

    # Enforce timestamp-named destination and keep using the initial timestamp folder.
    if [[ ! ${DIR_NAME} =~ ^[0-9]{14}$ ]]; then
        logging $LABEL_ERROR "save_logs skipped: invalid timestamp directory name (${DIR_NAME})"
        return 1
    fi

    JUDGE_DEST_DIR=${DEST_DIR}/judge_module_logs
    FLIGHT_RECORDER_DEST_DIR=${DEST_DIR}/flight_recorder_logs

    logging $LABEL_INFO "save_logs starts: ${DEST_DIR}"
    mkdir -p ${DEST_DIR}
    mkdir -p ${JUDGE_DEST_DIR}
    mkdir -p ${FLIGHT_RECORDER_DEST_DIR}

    # Preserve flight recorder artifacts from latest before replacing latest snapshot.
    if [ -e /tmp/share/logs/latest/data.json ]; then
        cp /tmp/share/logs/latest/data.json ${FLIGHT_RECORDER_DEST_DIR}/data.json
    fi

    mkdir -p ${DEST_DIR}/user_programs_logs
    if [ -d /tmp/share/logs/latest/user_programs_logs ]; then
        cp -a /tmp/share/logs/latest/user_programs_logs/. ${DEST_DIR}/user_programs_logs/
    fi
    extract_user_program_output_log ${DEST_DIR}/user_programs_logs/ros ${DEST_DIR}/user_programs_logs/user_program_output.log

    if [ -e ${HOME}/ib2.log ]; then
        cp ${HOME}/ib2.log ${FLIGHT_RECORDER_DEST_DIR}/$(basename ${HOME}/ib2.log)
    fi

    # Remove latest dir
    if [ -e ${LATEST_DIR} ]; then
        rm -r ${LATEST_DIR}
    fi

    if [ -e ${GAME_LOG} ]; then
        cp ${GAME_LOG} ${JUDGE_DEST_DIR}/$(basename ${GAME_LOG})
    else
        logging $LABEL_WARN "GAME_LOG not found: ${GAME_LOG}"
    fi

    if [ -e ${SYSTEM_LOG} ]; then
        cp ${SYSTEM_LOG} ${JUDGE_DEST_DIR}/$(basename ${SYSTEM_LOG})
    else
        logging $LABEL_WARN "SYSTEM_LOG not found: ${SYSTEM_LOG}"
    fi

    if [ -e ${RESULT_JSON} ]; then
        cp ${RESULT_JSON} ${JUDGE_DEST_DIR}/$(basename ${RESULT_JSON})
    else
        logging $LABEL_WARN "RESULT_JSON not found: ${RESULT_JSON}"
    fi

    if [ -e ${JUDGE_LOG} ]; then
        cp ${JUDGE_LOG} ${JUDGE_DEST_DIR}/$(basename ${JUDGE_LOG})
    else
        logging $LABEL_WARN "JUDGE_LOG not found: ${JUDGE_LOG}"
    fi

    if [ -e ${ROSBAG_LOG} ]; then
        cp ${ROSBAG_LOG} ${JUDGE_DEST_DIR}/$(basename ${ROSBAG_LOG})
    else
        logging $LABEL_WARN "ROSBAG_LOG not found: ${ROSBAG_LOG}"
    fi

    if [ -e ${STATUS_INDICATOR_LOG} ]; then
        cp ${STATUS_INDICATOR_LOG} ${JUDGE_DEST_DIR}/$(basename ${STATUS_INDICATOR_LOG})
    fi

    if [ -e ${FLIGHT_RECORDER_LOG} ]; then
        cp ${FLIGHT_RECORDER_LOG} ${FLIGHT_RECORDER_DEST_DIR}/$(basename ${FLIGHT_RECORDER_LOG})
    fi

    if [ -e ${JUDGE_WORK_DIR}/data.log ]; then
        cp ${JUDGE_WORK_DIR}/data.log ${JUDGE_DEST_DIR}/data.log
    fi

    if [ -e ${JUDGE_WORK_DIR}/localization_history.txt ]; then
        cp ${JUDGE_WORK_DIR}/localization_history.txt ${JUDGE_DEST_DIR}/localization_history.txt
    fi

    if [ -d ${TEXTURES_DIR} ]; then
        cp -r ${TEXTURES_DIR} ${DEST_DIR}/
    else
        logging $LABEL_WARN "textures directory not found: ${TEXTURES_DIR}"
    fi

    if [ -e ${ISS_URDF} ]; then
        cp ${ISS_URDF} ${DEST_DIR}/
    else
        logging $LABEL_WARN "iss.urdf not found: ${ISS_URDF}"
    fi

    # Check the existence of rosbag and copy it.
    if [ -e ${ROSBAG}.active ] || [ -e ${ROSBAG} ]; then
        # Wait until simulation.bag.active is renamed to simulation.bag
        while [ ! -e ${ROSBAG} ];
        do
            logging $LABEL_INFO "Waiting for rosbag to be generated..."
            sleep 2
        done
        cp ${ROSBAG} ${DEST_DIR}/$(basename ${ROSBAG})
    else
        logging $LABEL_ERROR "rosbag is not recorded"
    fi

    # Keep latest snapshot for consumers that read /tmp/share/logs/latest
    cp -r ${DEST_DIR} ${LATEST_DIR}
    ln -nfs ../${DIR_NAME} ${LATEST_DIR}/link_origin
    logging $LABEL_INFO "save_logs has done."
}

ready() {
    logging $LABEL_INFO "Unpause"
    gz_unpause
    logging $LABEL_INFO "On your mark..."
    while [ "$(rosparam get /krpc/judge_ready 2>&1)" != "true" ];
    do
        sleep 2;
    done
    logging $LABEL_INFO "Simulator is ready"
    rosparam set /krpc/ready true
}

go() {
    logging $LABEL_INFO "Waiting IB2 to be ready..."
    while [ "$(rosparam get /ib2_user/ready 2>&1)" != "true" ];
    do
        sleep 1;
    done
    logging $LABEL_INFO "IB2 is ready"
    logging $LABEL_INFO "Go"
    rostopic pub --once /ib2_user/start platform_msgs/UserLogic "id: 0" &>> ${SYSTEM_LOG} &
}

kill_user() {
    source /opt/ros/melodic/setup.bash
    source $BUILD_PATH/devel/setup.bash
    logging $LABEL_INFO "Stopping IB2..."
    rosservice call /ib2_user/stop "{}" && \
    logging $LABEL_INFO "Shutting down IB2..."
    rosnode kill /krpc_user
}

main() {
    logging_wait "NO VNC" ${WAIT_VNC}
    logging $LABEL_INFO "Start launcher."

    set_env && \
    set_timestamp && \
    set_random_env && \
    launch_simulation && \
    launch_judge_module && \
    launch_status_indicator_module && \
    launch_flight_recorder_module && \
    launch_record_rosbag && \
    ready && \
    go && \
    watch_dog || \
    catch_error

    kill_user || true
    force_exit
    save_logs

    logging $LABEL_INFO "End launcher."

    exit 0
}

main
