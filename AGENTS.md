# AGENTS.md

## 工作空间
- 根目录：`/home/goldesquemoon/Projects/MatchCar/dev_ws`；源码根 `src/origincar`（非默认 `src`）。
- `build/`、`install/`、`log/` 是 colcon 产物，不要改。
- 所有 colcon 命令必须带 `--base-paths src/origincar`。
- `.gitignore` 已忽略 `build/`、`install/`、`log/`。

## 构建与测试
- 先加载 ROS 2 Humble：`source /opt/ros/humble/setup.bash`
- 全量构建：`colcon build --symlink-install --base-paths src/origincar`
- 单包构建：`colcon build --symlink-install --base-paths src/origincar --packages-up-to <pkg>`
- 构建后加载 overlay：`source /home/goldesquemoon/Projects/MatchCar/dev_ws/install/setup.bash`
- 安装依赖：`rosdep install --from-paths src/origincar --ignore-src -r -y`
- 测试：`colcon test --base-paths src/origincar --packages-select <pkg> && colcon test-result --verbose`
- 现有包仅有 `ament_lint_auto` 检查，无单元测试。

## 包边界

| 包 | 类型 | 入口 / 作用 |
|---|---|---|
| `origincar_base` | C++ | 底盘串口节点 `origincar_base_node`；转换脚本 `cmd_vel_to_ackermann_drive.py`；主启动 `launch/origincar_bringup.launch.py` |
| `lslidar_driver` | C++ | 雷达节点 `lslidar_driver_node`（LifecycleNode）；N10 串口启动 `launch/lsn10_launch.py`，参数 `params/lidar_uart_ros2/lsn10.yaml` |
| `origincar_slam` | launch | `launch/slam.launch.py` 拉起雷达 + 底盘 bringup + slam_toolbox + teleop；`enable_teleop:=false` 关闭键盘 |
| `origincar_nav` | launch | `launch/navigation.launch.py` 拉起底盘 + 雷达 + nav2_bringup，地图 `origincar_slam/map/map_test.yaml`，参数 `config/nav2_params.yaml` |
| `origincar_description` | URDF | ROS 2 入口 `launch/display.launch.py`；同目录 `.launch` 文件是 ROS 1 旧式，不要用 |
| `origincar_msg` | msg | `Data.msg` (float32 x/y/z)、`Sign.msg` (int32 sign_data) |
| `lslidar_msgs` | msg | 雷达自定义消息 |
| `origincar_bringup` | launch | `usb_websocket_display.launch.py` 依赖外部 Hobot 包（`hobot_usb_cam`、`hobot_codec`、`dnn_node_example`、`websocket`），缺少则不可用 |
| `origincar_qr` | Python | `qr_scanner_node`（entry point）；扫码二维码数字 → 缓存结果 → 释放摄像头 → 等待 `/halfflag` 信号（std_msgs/Int32, 0/1）→ 执行动作；独立于 Hobot 管线，用 `/dev/video1` |
| `ackermann_msgs` | 3rd | AckermannDrive / AckermannDriveStamped |
| `serial` | 3rd | 串口库 |
| `teb_local_planner` | 3rd | Nav2 TEB 控制器插件；单元测试被注释，未启用 |
| `costmap_converter` | 3rd | TEB costmap 转换插件；有活跃的 gtest |

## 硬件与控制链路
```
cmd_vel (Twist)
  → cmd_vel_to_ackermann_drive.py (wheelbase=0.143m)
    → ackermann_cmd (AckermannDriveStamped)
      → origincar_base_node (串口协议 → STM32)
```
- 底盘串口帧格式（11 字节）：`0x7B` + id(2B) + speed(2B) + unused(2B) + angle(2B) + checksum + `0x7D`
- speed = linear.x * 1000，angle = steering_angle * 1000 / 2
- 默认串口 `/dev/wheeltec_controller` @ 115200，由 `base_serial.launch.py` 传入参数
- **sigintHandler 硬编码 `/dev/ttyCH343USB0`** — 若运行时改串口名，Ctrl-C 停车会写到错误串口
- 底盘发布话题：`odom`、`imu/data_raw`、`PowerVoltage`、`robotpose`、`robotvel`

## 坐标系链路
`map` → `odom_combined` → `base_footprint` → `laser`

改话题/坐标系/串口时同步检查：
- `origincar_base/launch/base_serial.launch.py`
- `origincar_base/config/ekf.yaml`
- `lslidar_driver/params/*.yaml`
- `origincar_slam/config/slam_params.yaml`
- `origincar_nav/config/nav2_params.yaml`

## 高风险坑点
- `lsn10.yaml` 参数根键是 `/lslidar_driver_node`，改节点名会导致参数不加载。
- `wheeltec_udev.sh` 写 `/etc/udev/rules.d/` 并重启 udev，宿主机级修改，非明确要求不要执行。
- 当前工作空间无 `tf2_tools` 源码包，如引入可能复现 `setup.py develop --uninstall` 兼容性问题。
- `origincar_base.cpp` 的 `Sign_Switch_Sub` 订阅 `/sign4return`（Int32），当前被注释掉。

## 新任务：扫描二维码
### 目标
新增二维码扫描功能：摄像头识别二维码中的数字，根据数字规律执行动作（如偶数→右转），识别结果 print 到终端屏幕。

### 已知摄像头管线
- `/dev/video0` 作为默认摄像头设备
- `origincar_bringup` 有基于 Hobot 的完整管线（usb_cam → codec → DNN → websocket），但依赖仓库外部包
- `config/` 下有多种 DNN 模型配置（YOLO、FCOS、MobileNet 等），用于 Hobot 视觉管线

### 开发建议
- 新建 ROS 2 Python 包（如 `origincar_qr`）或直接写 Python 节点
- 依赖：`cv_bridge`、`pyzbar`/`zbar`、`sensor_msgs`、`geometry_msgs`（publish `Twist` 到 `cmd_vel`）
- 直接订阅 `/image` 或使用 OpenCV 打开 `/dev/video0`
- 识别到数字后 publish `geometry_msgs/msg/Twist` 到 `cmd_vel` 即可控制小车

### docs/todo/ 目录
新建 `/home/goldesquemoon/Projects/MatchCar/dev_ws/docs/todo/` 放置任务进度 markdown 文件，不要提交到 `.gitignore`。

## Git 环境
- 全局 Git 身份：`user.name=yznn007`，`user.email=3181666393@qq.com`
- 提交前确认身份符合项目要求
## 项目背景
- **赛事**：全国大学生智能车竞赛（智慧医疗机器人创意赛）
- **上位机**：RDK X5（地瓜机器人/Horizon Robotics），系统 Ubuntu 22.04 + ROS 2 Humble
- 仓库根目录 `config/` 存放 DNN 模型配置，供 RDK X5 上 Hobot AI 推理节点使用

## 仓库范围
- 工作空间路径：`~/dev_ws`，源码根是 `src/origincar`，不是默认 ROS `src` 包根
- `build/`、`install/`、`log/` 是 `colcon` 产物，不要在这些目录改源码
- 包发现必须带 `--base-paths src/origincar`

## 常用命令
- 加载环境：`source /opt/ros/humble/setup.bash`
- 构建后加载 overlay：`source ~/dev_ws/install/setup.bash`
- 查看包列表：`colcon list --base-paths src/origincar`
- 安装源码依赖：`rosdep install --from-paths src/origincar --ignore-src -r -y`
- 全量构建：`colcon build --symlink-install --base-paths src/origincar`
- 单包及依赖构建：`colcon build --symlink-install --base-paths src/origincar --packages-up-to <pkg>`
- 包级测试：`colcon test --base-paths src/origincar --packages-select <pkg> && colcon test-result --verbose`

## 首次安装依赖

### 系统依赖
```bash
sudo apt update && sudo apt install -y \
  python3-colcon-common-extensions python3-rosdep \
  libpcap-dev libpcl-dev libopencv-dev libzbar-dev \
  ros-humble-diagnostic-updater ros-humble-nav2-msgs \
  ros-humble-pcl-conversions ros-humble-robot-localization \
  ros-humble-imu-filter-madgwick ros-humble-slam-toolbox \
  ros-humble-teleop-twist-keyboard ros-humble-rviz2 \
  ros-humble-xacro ros-humble-joint-state-publisher \
  ros-humble-robot-state-publisher
```

### pip 依赖
```bash
pip install opencv-python pyzbar
```

### rosdep
```bash
sudo rosdep init && rosdep update
rosdep install --from-paths src/origincar --ignore-src -r -y
```

### 外部包（可选）
origincar_bringup 依赖 RDK X5 SDK 的 Hobot 包，需单独安装。

## 包边界与入口
- `origincar_base`：底盘节点 `origincar_base_node`，转换脚本 `cmd_vel_to_ackermann_drive.py`，主启动 `launch/origincar_bringup.launch.py`
- `origincar_base/launch/origincar_bringup.launch.py` 会包含 `base_serial.launch.py`、`robot_mode_description.launch.py`（模型发布）、`imu_filter_madgwick_node` 和 EKF；`carto_slam:=true` 时跳过 EKF
- `lslidar_driver`：雷达可执行文件 `lslidar_driver_node`；N10 串口启动 `launch/lsn10_launch.py` 使用 `params/lidar_uart_ros2/lsn10.yaml`
- `origincar_slam/launch/slam.launch.py` 直接拉起雷达、`origincar_base` bringup、`slam_toolbox` 和默认开启的 `teleop_twist_keyboard`；可用 `enable_teleop:=false` 关闭键盘节点
- `origincar_nav/launch/navigation.launch.py` 直接拉起底盘、雷达和 `nav2_bringup`，默认地图来自 `origincar_slam/map/map_v0.1.yaml`（注意不是 `map_test.yaml`），参数是 `origincar_nav/config/nav2_params.yaml`
- `origincar_description`：只包含 `urdf/` 和 `meshes/`，无 launch 目录；实际模型加载由 `origincar_base/launch/robot_mode_description.launch.py` 完成，入口 xacro 是 `urdf/origincar.xacro`
- `origincar_description/urdf/origincar_stl.xacro` 是独立的 STL 网格模型文件（使用真实 STL mesh），与 `origincar.xacro`（使用几何体）是两套独立模型，目前 launch 加载的是 `origincar.xacro`
- `origincar_qr`：二维码扫描包，C++ 节点 `qr_scanner_node`（libzbar）和 Python 节点 `qr_scanner_py_node`（pyzbar + cv2 兜底），详见 `src/origincar/origincar_qr/AGENTS.md`
- `origincar_qr` Python 节点需要 pip 依赖：`pip install opencv-python pyzbar`
- 接口包：`origincar_msg`、`lslidar_msgs`、`ackermann_msgs`、`teb_msgs`、`costmap_converter_msgs`
- 第三方源码包：`serial`、`teb_local_planner`、`costmap_converter`；Nav2 参数依赖 TEB/Costmap converter 相关包
- `origincar_bringup` 依赖仓库外 Hobot 包（如 `hobot_usb_cam`、`hobot_codec`、`dnn_node_example`、`websocket`），缺少时该包不可用

## 高风险坑点
- `origincar_base/src/origincar_base.cpp:350` 构造函数默认串口是 `/dev/ttyCH343USB0`；常规启动靠 `base_serial.launch.py` 覆盖为 `/dev/wheeltec_controller`
- `origincar_base/src/origincar_base.cpp:402` 的 `sigintHandler` 硬编码 `/dev/ttyCH343USB0`；运行时改 `usart_port_name`，Ctrl-C 停车指令会写到错误串口
- `lslidar_driver/params/lidar_uart_ros2/lsn10.yaml` 参数根键是 `/lslidar_driver_node`；改节点名会导致参数不加载
- `wheeltec_udev.sh`（及同目录 `wheeltec_udev` 脚本）会写 `/etc/udev/rules.d/` 并重启 udev，属于宿主机级修改；未明确要求不要执行
- 两套 xacro 模型（`origincar.xacro` 几何体 vs `origincar_stl.xacro` STL 网格）的激光雷达表示不一致：`origincar.xacro` 中 laser link 仍用圆柱体占位，`origincar_stl.xacro` 已使用 `lslidar_N10.stl` 真实模型；修改模型时注意同步
- lslidar_N10.stl 是米制单位（已从毫米转换），与其他 STL 文件一致

## 联调一致性
- 默认链路：雷达发布 `/scan`，SLAM/Nav2 订阅 `/scan`，EKF/SLAM/Nav2 使用 `odom_combined` 与 `base_footprint`
- 改话题、坐标系或串口时同步检查：`origincar_base/launch/base_serial.launch.py`、`origincar_base/config/ekf.yaml`、`lslidar_driver/params/*.yaml`、`origincar_slam/config/slam_params.yaml`、`origincar_nav/config/nav2_params.yaml`

## 导航栈特殊配置
- 局部规划器使用 **TEB**（非默认 RPP），配置了阿克曼运动学约束（最小转弯半径 0.4m）
- 全局规划器使用 **Hybrid A***（非默认 NavFn）
- 机器人轮廓已定义为多边形（非圆形）：`[[0.138, 0.082], [0.138, -0.082], [-0.138, -0.082], [-0.138, 0.082]]`
- RPP 备份配置已注释在 `nav2_params.yaml` 中，可快速回滚对比

## 坐标系与话题链路
```
map → odom_combined → base_footprint → laser
      (EKF 输出)      (底盘基座)      (雷达)
```
- 关键话题：`/scan`（雷达）、`cmd_vel`（速度控制）、`ackermann_cmd`（转向控制）、`odom_combined`（里程计）、`/imu/data`（IMU）

## 其他资源
- `origincar_qr` 包有独立 AGENTS.md，详见 `src/origincar/origincar_qr/AGENTS.md`
- DNN 模型配置（供 RDK X5 Hobot 推理节点使用）位于 `config/` 和 `src/origincar/config/`

## Git 环境
- 全局 Git 身份：`user.name=yznn007`，`user.email=3181666393@qq.com`；提交前按项目要求确认身份
