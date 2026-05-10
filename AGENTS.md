# AGENTS.md

## 仓库范围
- 工作空间根目录是 `/home/sunrise/dev_ws`；源码根是 `src/origincar`，不是默认 ROS `src` 包根。
- `build/`、`install/`、`log/` 是 `colcon` 产物，不要在这些目录改源码。
- 包发现必须带 `--base-paths src/origincar`，否则容易漏包或按错误工作空间推断。

## 常用命令
- 先加载 ROS 2 Humble：`source /opt/ros/humble/setup.bash`。
- 查看实际包列表：`colcon list --base-paths src/origincar`。
- 安装源码依赖：`rosdep install --from-paths src/origincar --ignore-src -r -y`。
- 全量构建：`colcon build --symlink-install --base-paths src/origincar`。
- 单包及依赖构建：`colcon build --symlink-install --base-paths src/origincar --packages-up-to <pkg>`。
- 构建后加载 overlay：`source /home/sunrise/dev_ws/install/setup.bash`。
- 包级测试：`colcon test --base-paths src/origincar --packages-select <pkg> && colcon test-result --verbose`。

## 包边界与入口
- `origincar_base`：底盘节点 `origincar_base_node`，转换脚本 `cmd_vel_to_ackermann_drive.py`，主启动 `launch/origincar_bringup.launch.py`。
- `origincar_base/launch/origincar_bringup.launch.py` 会包含 `base_serial.launch.py`、模型发布、`imu_filter_madgwick_node` 和 EKF；`carto_slam:=true` 时跳过 EKF。
- `lslidar_driver`：雷达可执行文件 `lslidar_driver_node`；N10 串口启动 `launch/lsn10_launch.py` 使用 `params/lidar_uart_ros2/lsn10.yaml`。
- `origincar_slam/launch/slam.launch.py` 直接拉起雷达、`origincar_base` bringup、`slam_toolbox` 和默认开启的 `teleop_twist_keyboard`；可用 `enable_teleop:=false` 关闭键盘节点。
- `origincar_nav/launch/navigation.launch.py` 直接拉起底盘、雷达和 `nav2_bringup`，默认地图来自 `origincar_slam/map/map_test.yaml`，参数是 `origincar_nav/config/nav2_params.yaml`。
- `origincar_description` 的 ROS 2 入口是 `launch/display.launch.py`；同目录还有旧式 `.launch` 文件，不要误当 ROS 2 Python launch。
- 接口包：`origincar_msg`、`lslidar_msgs`、`ackermann_msgs`、`teb_msgs`、`costmap_converter_msgs`。
- 第三方源码包：`serial`、`teb_local_planner`、`costmap_converter`；Nav2 参数依赖 TEB/Costmap converter 相关包。
- `origincar_bringup/launch/usb_websocket_display.launch.py` 依赖仓库外 Hobot 包（如 `hobot_usb_cam`、`hobot_codec`、`dnn_node_example`、`websocket`）。

## 高风险坑点
- `origincar_base/src/origincar_base.cpp` 构造函数默认串口是 `/dev/ttyCH343USB0`；常规启动靠 `base_serial.launch.py` 覆盖为 `/dev/wheeltec_controller`。
- `origincar_base/src/origincar_base.cpp` 的 `sigintHandler` 仍硬编码 `/dev/ttyCH343USB0`；若运行时改 `usart_port_name`，Ctrl-C 停车指令可能写到错误串口。
- `lslidar_driver/params/lidar_uart_ros2/lsn10.yaml` 参数根键是 `/lslidar_driver_node`；改节点名会导致参数不加载。
- `wheeltec_udev.sh` 会写 `/etc/udev/rules.d/` 并重启 udev，属于宿主机级修改；未明确要求不要执行。
- 当前工作空间没有 `tf2_tools` 源码包；如果后续重新引入，可能复现 `setup.py develop --uninstall` 兼容性问题。

## 联调一致性
- 默认链路：雷达发布 `/scan`，SLAM/Nav2 订阅 `/scan`，EKF/SLAM/Nav2 使用 `odom_combined` 与 `base_footprint`。
- 改话题、坐标系或串口时同步检查：`origincar_base/launch/base_serial.launch.py`、`origincar_base/config/ekf.yaml`、`lslidar_driver/params/*.yaml`、`origincar_slam/config/slam_params.yaml`、`origincar_nav/config/nav2_params.yaml`。

## Git 环境
- 当前环境已配置全局 Git 身份（`user.name=yznn007`，`user.email=3181666393@qq.com`）；提交前仍按项目要求确认身份。
