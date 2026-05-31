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
