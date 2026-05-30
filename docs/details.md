# OriginCar 详细文档

## 工作空间结构

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
│       ├── wheeltec_udev
│       └── wheeltec_udev.sh
├── config/
├── build/
├── install/
├── log/
└── README.md
```

## 包说明

| 包名 | 路径 | 类型 | 作用 |
|---|---|---|---|
| `origincar_base` | `src/origincar/origincar_base` | `ament_cmake` | 底盘串口通信、里程计/IMU发布、速度控制 |
| `origincar_slam` | `src/origincar/origincar_slam` | `ament_cmake` | 建图启动与参数 |
| `origincar_nav` | `src/origincar/origincar_nav` | `ament_cmake` | Nav2 导航启动、参数与行为树 |
| `lslidar_driver` | `src/origincar/lslidar_driver` | `ament_cmake` | 雷神雷达驱动节点 |
| `lslidar_msgs` | `src/origincar/lslidar_msgs` | `ament_cmake` | 雷达消息定义 |
| `origincar_description` | `src/origincar/origincar_description` | `ament_cmake` | 机器人 URDF 模型与 STL 网格文件（由 `origincar_base` 的 launch 加载） |
| `origincar_msg` | `src/origincar/origincar_msg` | `ament_cmake` | 业务自定义消息 |
| `origincar_bringup` | `src/origincar/origincar_bringup` | `ament_cmake` | USB/Websocket 组合启动（依赖仓库外 Hobot 包） |
| `ackermann_msgs` | `src/origincar/3rdparty/ackermann_msgs-ros2` | `ament_cmake` | Ackermann 控制消息 |
| `serial` | `src/origincar/3rdparty/serial_ros2` | `ament_cmake` | 串口通信库 |
| `teb_local_planner` / `teb_msgs` | `src/origincar/3rdparty/teb_local_planner` | `ament_cmake` | Nav2 使用的 TEB 控制器及消息 |
| `costmap_converter` / `costmap_converter_msgs` | `src/origincar/3rdparty/costmap_converter` | `ament_cmake` | TEB 相关 costmap 转换插件及消息 |

`origincar_bringup` 的 `usb_websocket_display.launch.py` 依赖外部包（例如 `hobot_usb_cam`、`hobot_codec`、`dnn_node_example`、`websocket`），缺少这些包时该启动不可用。

> **模型说明**：`origincar_description/urdf/` 下有两套 xacro 模型（`origincar.xacro` 几何体 / `origincar_stl.xacro` STL 网格），当前 launch 加载前者，修改模型时注意两套同步。

## 话题与坐标系

### 主要话题

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

### 常用坐标系

- `map`
- `odom_combined`
- `base_footprint`
- `laser`

注意：底盘、雷达、SLAM 的坐标系命名必须一致，否则会出现 TF 不连通或定位异常。

## 关键配置（串口、雷达、SLAM、导航参数）

### 串口与底盘参数

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
cd ~/dev_ws
sudo bash src/origincar/wheeltec_udev.sh
```

### 雷达参数

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

### SLAM 参数

SLAM 参数文件：

- `src/origincar/origincar_slam/config/slam_params.yaml`

常改项：

- `map_frame`
- `odom_frame`
- `base_frame`
- `scan_topic`
- `resolution`

### 导航参数

导航启动文件：

- `src/origincar/origincar_nav/launch/navigation.launch.py`

导航参数文件：

- `src/origincar/origincar_nav/config/nav2_params.yaml`

默认行为树：

- `src/origincar/origincar_nav/behavior_trees/navigate_to_pose_ackermann.xml`

默认地图：

- `src/origincar/origincar_slam/map/map_v0.1.yaml`

注意：导航参数中的 `/scan`、`odom_combined`、`base_footprint` 需要与底盘、雷达、SLAM 配置保持一致。

## 串口配置

设备使用 udev 规则设置串口别名，详见 [udev 使用教程](udev.md)。

| 设备 | 别名 | 用途 |
|------|------|------|
| 雷达 | `/dev/wheeltec_lidar` | N10 串口激光雷达 |
| 底盘 | `/dev/wheeltec_controller` | 底盘串口通信 |
| IMU/GNSS | `/dev/wheeltec_FDI_IMU_GNSS` | IMU/GNSS 模块 |
| 麦克风 | `/dev/wheeltec_mic` | 麦克风设备 |

安装 udev 规则：
```bash
sudo bash src/origincar/wheeltec_udev.sh
```

## 常见故障排查

### 串口打不开

现象：日志出现 `can not open serial port`。

排查步骤：

```bash
ls -l /dev/ttyACM* /dev/ttyUSB* /dev/wheeltec_* 2>/dev/null
groups
```

- 确认当前用户在 `dialout` 组
- 检查 `base_serial.launch.py` 中 `usart_port_name`
- 如使用别名设备，重新执行 udev 脚本后重插设备

### 没有 `/scan`

- 确认雷达节点已启动：`ros2 node list`
- 确认话题是否存在：`ros2 topic list`
- 检查 `lsn10.yaml` 中 `serial_port_` 与 `pubScan: true`
- 检查 `interface_selection` 与实际连接方式（`serial`/`net`）一致

### 依赖缺失

`origincar_base` 缺少 `nav2_msgs`：

```bash
sudo apt install -y ros-humble-nav2-msgs
```

`lslidar_driver` 缺少 `diagnostic_updater`：

```bash
sudo apt install -y ros-humble-diagnostic-updater
```

### `tf2_tools` 构建问题

当前工作空间不包含 `tf2_tools` 源码包。若需 `view_frames` 等工具，直接安装系统包：

```bash
sudo apt install -y ros-humble-tf2-tools
```
