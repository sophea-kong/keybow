#!/bin/bash

LOG_FILE="${1:-${ROS_LOG_DIR:-${HOME}/.ros/log}/krpc_user_console.log}"

tail -n +1 -F "${LOG_FILE}"
