# Kibo-RPC 7th Simulator

This workspace is used to develop programs for Kibo-RPC 7th and test them with the Web simulator or the local simulator.

For environment setup, API specifications, and detailed programming instructions, see the [Programming Manual](docs/ProgrammingManual.md).

## Before You Start

- Work in Linux or Ubuntu on WSL2.
- Docker is required when using the local simulator.
- The main directory for participant code is `users/catkin_ws/src/krpc_user/`.
- Do not modify provided files such as `docker/`, `rootfs/`, `rviz/`, `krpc_api_server`, or `krpc_ib2_msgs` unless necessary.

## Basic Usage

### 1. Edit Your Program

Edit the sample program in `users/catkin_ws/src/krpc_user/`.
Do not change the package name, `CMakeLists.txt`, `package.xml`, or launch file names.

### 2. Create a Submission Package

From the project root directory, run:

```bash
cd users
bash ./packing.sh my_submission
```

This creates `users/my_submission.tar.gz`. Upload this file to the Web simulator to run your program.

The Web simulator is available at:

- [Kibo-RPC Login Page](https://jaxa.krpc.jp/user-auth)

### 3. Use the Local Simulator

Build the Docker image the first time you use the local simulator or when the image is updated.

```bash
bash ./build.sh
```

Then, start the simulator in another terminal:

```bash
bash ./simulation.sh
```

While the simulator is running, open <http://localhost> in a browser to view it.
Your program is built and started automatically by `simulation.sh`.

To stop the simulation, press `Ctrl+C` in the terminal where it is running.

### 4. Check Results and Logs

Execution results are saved in `share/logs/`. The latest results are available in `share/logs/latest/`.

## Replay

To replay a rosbag created by a simulation, run:

```bash
bash ./replay.sh
```

You can specify the playback speed and start time as arguments:

```bash
bash ./replay.sh <playback_speed> <start_time>
```

## More Information

The Programming Manual explains the following topics in detail:

- WSL2, Ubuntu, and Docker setup
- Submitting programs to the Web simulator and checking results
- Detailed instructions for using the local simulator
- Sample program structure and editing procedures
- ROS APIs, movement, camera, and checkpoint processing
- Log design, error handling, and AR marker recognition

For details, see [docs/ProgrammingManual.md](docs/ProgrammingManual.md).

# keybow
