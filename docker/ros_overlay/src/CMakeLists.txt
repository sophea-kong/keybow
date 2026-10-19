cmake_minimum_required(VERSION 3.0.2)
project(catkin_workspace)

find_package(catkin REQUIRED)

# Local packages (ROS message types and KRPC-specific extensions)
add_subdirectory(ib2_msgs)
add_subdirectory(krpc_msgs)
add_subdirectory(platform_sim/krpc_description krpc_description)

# Upstream core packages (JAXA Int-Ball2 simulator)
add_subdirectory(../src_upstream/Int-Ball2_platform_simulator/src/flight_software flight_software)
add_subdirectory(../src_upstream/Int-Ball2_platform_simulator/src/platform platform)
add_subdirectory(../src_upstream/Int-Ball2_platform_simulator/src/user user)

catkin_metapackage()
