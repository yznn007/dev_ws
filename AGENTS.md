# AGENTS.md

## 范围与源代码位置
- 工作空间根目录是 `/home/sunrise/dev_ws`；实际源码在 `src/origincar`。
- `build/`、`install/`、`log/` 是 `colcon` 产物，不要在这些目录改代码。
- 本仓库包发现依赖 `--base-paths src/origincar`（不是默认 `src`）。

## 常用命令（已验证）
- 先加载 ROS 2 环境：`source /opt/ros/humble/setup.bash`。
- 查看包：`colcon list --base-paths src/origincar`
- 安装源码依赖：`rosdep install --from-paths src/origincar --ignore-src -r -y`
- 全量构建：`colcon build --symlink-install --base-paths src/origincar`
- 单包/增量构建：`colcon build --symlink-install --base-paths src/origincar --packages-up-to <pkg>`
- 每次构建后重新加载：`source /home/sunrise/dev_ws/install/setup.bash`
- 包级测试/检查：`colcon test --base-paths src/origincar --packages-select <pkg> && colcon test-result --verbose`

## 包边界与真实入口
- `origincar_base`：底盘主节点 `origincar_base_node`，以及 `scripts/cmd_vel_to_ackermann_drive.py`；主 bringup 在 `origincar_base/launch/origincar_bringup.launch.py`。
- `lslidar_driver`：雷达可执行文件是 `lslidar_driver_node`，参数在 `lslidar_driver/params`。
- `origincar_slam`：`launch/slam.launch.py` 组装底盘 + 雷达 + `slam_toolbox` + `teleop_twist_keyboard`。
- `origincar_description`：ROS 2 入口是 `launch/display.launch.py`。
- 接口包：`origincar_msg`、`lslidar_msgs`、`ackermann_msgs`（消息定义）。
- 第三方包：`serial`（`3rdparty/serial_ros2`）。
- `origincar_bringup` 仅安装 `usb_websocket_display.launch.py`，该启动依赖仓库外 Hobot 包（如 `hobot_usb_cam`、`hobot_codec`、`dnn_node_example`、`websocket`）。

## 已验证的高风险坑点
- `origincar_base/src/origincar_base.cpp` 的 `sigintHandler` 仍硬编码 `/dev/ttyCH343USB0`；若运行时改了 `usart_port_name`，Ctrl-C 发送停车指令可能写到错误串口。
- `origincar_base/src/origincar_base.cpp` 构造函数默认串口也是 `/dev/ttyCH343USB0`；通过 `base_serial.launch.py` 覆盖为 `/dev/wheeltec_controller` 时才会按 launch 参数运行。
- `lslidar_driver/params/lidar_uart_ros2/lsn10.yaml` 参数根键是 `/lslidar_driver_node`；改节点名会导致参数不加载。
- `origincar_description/launch` 同时存在旧 ROS1 `.launch` 与 ROS2 `.launch.py`；ROS2 应优先使用 `display.launch.py`。
- `wheeltec_udev.sh` 会直接写 `/etc/udev/rules.d/` 并重启 udev，属于宿主机级修改；未被明确要求时不要执行。
- 当前工作空间没有第三方 `tf2_tools` 包；若后续重新引入该包，可能再次遇到 `setup.py develop --uninstall` 的兼容性问题。

## 联调时要保持一致的配置
- 默认链路：雷达发布 `/scan`，SLAM 订阅 `/scan`，EKF/SLAM 使用 `odom_combined` 与 `base_footprint`。
- 修改话题或坐标系时，至少同步检查：
  - `origincar_base/launch/base_serial.launch.py`
  - `origincar_base/config/ekf.yaml`
  - `lslidar_driver/params/*.yaml`
  - `origincar_slam/config/slam_params.yaml`

## Git 环境（车端）
- 已安装 `git`（`git version 2.34.1`）。
- 全局 `user.name` 与 `user.email` 默认为空，按项目要求手动配置。
