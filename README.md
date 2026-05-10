# OriginCar ROS 2 工作空间

## 1) 项目简介

本仓库是基于 ROS 2 Humble 的小车工作空间，包含底盘串口驱动、雷达驱动、SLAM/导航启动、机器人模型、自定义消息与导航相关第三方源码包。

- 工作空间路径：`/home/sunrise/dev_ws`
- 源码主路径：`/home/sunrise/dev_ws/src/origincar`
- 包发现参数：`--base-paths src/origincar`

## 2) 快速开始

### 2.1 环境要求

- Ubuntu 22.04
- ROS 2 Humble
- Python3 / C++14

### 2.2 安装系统依赖

```bash
sudo apt update
sudo apt install -y \
  python3-colcon-common-extensions \
  python3-rosdep \
  libpcap-dev \
  libpcl-dev \
  ros-humble-diagnostic-updater \
  ros-humble-nav2-msgs \
  ros-humble-pcl-conversions \
  ros-humble-robot-localization \
  ros-humble-imu-filter-madgwick \
  ros-humble-slam-toolbox \
  ros-humble-teleop-twist-keyboard \
  ros-humble-rviz2 \
  ros-humble-xacro \
  ros-humble-joint-state-publisher \
  ros-humble-robot-state-publisher
```

首次使用 `rosdep` 时执行：

```bash
sudo rosdep init
rosdep update
```

安装源码依赖：

```bash
cd /home/sunrise/dev_ws
source /opt/ros/humble/setup.bash
rosdep install --from-paths src/origincar --ignore-src -r -y
```

### 2.3 构建与环境加载

```bash
cd /home/sunrise/dev_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --base-paths src/origincar
source /home/sunrise/dev_ws/install/setup.bash
```

可选：写入 `~/.bashrc`。

```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
echo "source /home/sunrise/dev_ws/install/setup.bash" >> ~/.bashrc
```

## 3) 常用启动（底盘/雷达/SLAM/导航）

执行前先加载环境：

```bash
source /opt/ros/humble/setup.bash
source /home/sunrise/dev_ws/install/setup.bash
```

### 3.1 底盘启动（推荐入口）

```bash
ros2 launch origincar_base origincar_bringup.launch.py
```

该启动会组合：底盘串口节点、Ackermann 转换节点、模型发布、IMU 滤波与 EKF。

若要临时关闭 EKF（`carto_slam:=true`）：

```bash
ros2 launch origincar_base origincar_bringup.launch.py carto_slam:=true
```

仅启动底盘串口节点：

```bash
ros2 launch origincar_base base_serial.launch.py akmcar:=false
```

### 3.2 雷达启动

N10 串口启动：

```bash
ros2 launch lslidar_driver lsn10_launch.py
```

常用可选启动：

- `ros2 launch lslidar_driver lsn10p_launch.py`
- `ros2 launch lslidar_driver lsm10_uart_launch.py`
- `ros2 launch lslidar_driver lsn10_net_launch.py`
- `ros2 launch lslidar_driver lsm10_net_launch.py`

雷达可视化：

```bash
ros2 launch lslidar_driver viewer_scan_launch.py
```

### 3.3 SLAM 启动

```bash
ros2 launch origincar_slam slam.launch.py
```

该启动会拉起：

- `lslidar_driver_node`
- `origincar_base` 的 bringup
- `slam_toolbox`（异步建图）
- `teleop_twist_keyboard`（默认开启）

如不需要键盘控制：

```bash
ros2 launch origincar_slam slam.launch.py enable_teleop:=false
```

### 3.4 导航启动

```bash
ros2 launch origincar_nav navigation.launch.py
```

该启动会拉起底盘、雷达和 Nav2，默认地图为 `origincar_slam/map/map.yaml`，默认参数为 `origincar_nav/config/nav2_params.yaml`。

## 4) 工作空间结构

```text
dev_ws/
├── src/
│   └── origincar/
│       ├── 3rdparty/
│       │   ├── ackermann_msgs-ros2/
│       │   ├── costmap_converter/
│       │   ├── serial_ros2/
│       │   └── teb_local_planner/
│       ├── lslidar_driver/
│       ├── lslidar_msgs/
│       ├── origincar_base/
│       ├── origincar_bringup/
│       ├── origincar_description/
│       ├── origincar_nav/
│       ├── origincar_msg/
│       └── origincar_slam/
├── build/
├── install/
├── log/
└── README.md
```

## 5) 包说明

| 包名 | 路径 | 类型 | 作用 |
|---|---|---|---|
| `origincar_base` | `src/origincar/origincar_base` | `ament_cmake` | 底盘串口通信、里程计/IMU发布、速度控制 |
| `origincar_slam` | `src/origincar/origincar_slam` | `ament_cmake` | 建图启动与参数 |
| `origincar_nav` | `src/origincar/origincar_nav` | `ament_cmake` | Nav2 导航启动、参数与行为树 |
| `lslidar_driver` | `src/origincar/lslidar_driver` | `ament_cmake` | 雷神雷达驱动节点 |
| `lslidar_msgs` | `src/origincar/lslidar_msgs` | `ament_cmake` | 雷达消息定义 |
| `origincar_description` | `src/origincar/origincar_description` | `ament_cmake` | 机器人模型与 RViz 配置 |
| `origincar_msg` | `src/origincar/origincar_msg` | `ament_cmake` | 业务自定义消息 |
| `origincar_bringup` | `src/origincar/origincar_bringup` | `ament_cmake` | USB/Websocket 组合启动（依赖仓库外 Hobot 包） |
| `ackermann_msgs` | `src/origincar/3rdparty/ackermann_msgs-ros2` | `ament_cmake` | Ackermann 控制消息 |
| `serial` | `src/origincar/3rdparty/serial_ros2` | `ament_cmake` | 串口通信库 |
| `teb_local_planner` / `teb_msgs` | `src/origincar/3rdparty/teb_local_planner` | `ament_cmake` | Nav2 使用的 TEB 控制器及消息 |
| `costmap_converter` / `costmap_converter_msgs` | `src/origincar/3rdparty/costmap_converter` | `ament_cmake` | TEB 相关 costmap 转换插件及消息 |

`origincar_bringup` 的 `usb_websocket_display.launch.py` 依赖外部包（例如 `hobot_usb_cam`、`hobot_codec`、`dnn_node_example`、`websocket`），缺少这些包时该启动不可用。

## 6) 话题与坐标系

### 6.1 主要话题

`origincar_base`：

- 订阅：`cmd_vel`（`geometry_msgs/Twist`）
- 订阅：`ackermann_cmd`（`ackermann_msgs/AckermannDriveStamped`）
- 发布：`odom`（`nav_msgs/Odometry`）
- 发布：`imu/data_raw`（`sensor_msgs/Imu`）
- 发布：`PowerVoltage`（`std_msgs/Float32`）
- 发布：`robotpose`（`origincar_msg/Data`）
- 发布：`robotvel`（`origincar_msg/Data`）

`lslidar_driver`：

- 发布：`/scan`（默认开启）
- 发布：`/lslidar_point_cloud`（按参数开启）

### 6.2 常用坐标系

- `map`
- `odom_combined`
- `base_footprint`
- `laser`

注意：底盘、雷达、SLAM 的坐标系命名必须一致，否则会出现 TF 不连通或定位异常。

## 7) 关键配置（串口、雷达、SLAM、导航参数）

### 7.1 串口与底盘参数

底盘启动参数在：

- `src/origincar/origincar_base/launch/base_serial.launch.py`

常改项：

- `usart_port_name`（默认 `/dev/wheeltec_controller`）
- `serial_baud_rate`
- `robot_frame_id`
- `odom_frame_id`
- `akmcar`

udev 规则脚本：

- `src/origincar/wheeltec_udev.sh`

执行示例（会修改宿主机 `/etc/udev/rules.d/`，请确认后执行）：

```bash
cd /home/sunrise/dev_ws
sudo bash src/origincar/wheeltec_udev.sh
```

### 7.2 雷达参数

N10 串口参数文件：

- `src/origincar/lslidar_driver/params/lidar_uart_ros2/lsn10.yaml`

常改项：

- `serial_port_`
- `scan_topic`
- `frame_id`
- `min_range` / `max_range`
- `pubScan` / `pubPointCloud2`
- `interface_selection`

注意：该文件参数根键为 `/lslidar_driver_node`，需与节点名保持一致。

### 7.3 SLAM 参数

SLAM 参数文件：

- `src/origincar/origincar_slam/config/slam_params.yaml`

常改项：

- `map_frame`
- `odom_frame`
- `base_frame`
- `scan_topic`
- `resolution`

### 7.4 导航参数

导航启动文件：

- `src/origincar/origincar_nav/launch/navigation.launch.py`

导航参数文件：

- `src/origincar/origincar_nav/config/nav2_params.yaml`

默认行为树：

- `src/origincar/origincar_nav/behavior_trees/navigate_to_pose_ackermann.xml`

默认地图：

- `src/origincar/origincar_slam/map/map.yaml`

注意：导航参数中的 `/scan`、`odom_combined`、`base_footprint` 需要与底盘、雷达、SLAM 配置保持一致。

## 8) 常见故障（串口、/scan、依赖缺失、tf2_tools）

### 8.1 串口打不开

现象：日志出现 `can not open serial port`。

排查步骤：

```bash
ls -l /dev/ttyACM* /dev/ttyUSB* /dev/wheeltec_* 2>/dev/null
groups
```

- 确认当前用户在 `dialout` 组
- 检查 `base_serial.launch.py` 中 `usart_port_name`
- 如使用别名设备，重新执行 udev 脚本后重插设备

### 8.2 没有 `/scan`

- 确认雷达节点已启动：`ros2 node list`
- 确认话题是否存在：`ros2 topic list`
- 检查 `lsn10.yaml` 中 `serial_port_` 与 `pubScan: true`
- 检查 `interface_selection` 与实际连接方式（`serial`/`net`）一致

### 8.3 依赖缺失

`origincar_base` 缺少 `nav2_msgs`：

```bash
sudo apt install -y ros-humble-nav2-msgs
```

`lslidar_driver` 缺少 `diagnostic_updater`：

```bash
sudo apt install -y ros-humble-diagnostic-updater
```

### 8.4 `tf2_tools` 构建问题

历史版本中，若工作空间包含第三方 `tf2_tools` 且出现 `setup.py develop --uninstall` 相关报错，可先跳过该包：

```bash
cd /home/sunrise/dev_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --base-paths src/origincar --packages-skip tf2_tools
```

若仅需工具命令，可直接安装系统包：

```bash
sudo apt install -y ros-humble-tf2-tools
```

## 9) 常用命令速查

```bash
# ssh连接
ssh -Y sunrise@192.168.31.181

# 进入工作空间
cd ~/dev_ws

# 加载 ROS 环境
source /opt/ros/humble/setup.bash

# 构建所有功能包
colcon build --symlink-install --base-paths src/origincar

# 构建单个功能包及依赖
colcon build --symlink-install --base-paths src/origincar --packages-up-to <功能包>

# 构建后加载 overlay
source ~/dev_ws/install/setup.bash


source ~/.bashrc

# 查看包
colcon list --base-paths src/origincar

# 查看节点与话题
ros2 node list
ros2 topic list

# 检查N10激光雷达硬件设备
ll /dev | grep ttyCH343USB*

# 代理设置,将 Proxy 行注释掉即可
nano ~/.bashrc
nano ~/.ssh/config

# 测试分布式通信
ros2 run demo_nodes_cpp talker
ros2 run demo_nodes_py listener

# 建图节点
ros2 launch origincar_slam slam.launch.py

# 摄像头节点
ros2 launch origincar_bringup usb_websocket_display.launch.py
192.168.31.181:8000
# 底盘节点
ros2 launch origincar_base origincar_bringup.launch.py    
# 键盘控制节点
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# 地图保存
ros2 run nav2_map_server map_saver_cli -f ~/dev_ws/src/origincar/origincar_slam/map/map

# 导航节点
ros2 launch origincar_nav navigation.launch.py
```
