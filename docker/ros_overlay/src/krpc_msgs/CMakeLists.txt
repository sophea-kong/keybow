cmake_minimum_required(VERSION 2.8.3)
project(krpc_msgs)

find_package(catkin REQUIRED COMPONENTS
  roscpp
  std_msgs
  message_generation
)

add_message_files(
  FILES
  QrReport.msg
)

generate_messages(
  DEPENDENCIES
  std_msgs 
  krpc_msgs
)

catkin_package(
  CATKIN_DEPENDS 
  message_generation
  std_msgs 
  roscpp 
  message_runtime
)

include_directories(
  ${catkin_INCLUDE_DIRS}
)
