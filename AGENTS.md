# AGENTS.md

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

## 包边界与入口
- `origincar_base`：底盘节点 `origincar_base_node`，转换脚本 `cmd_vel_to_ackermann_drive.py`，主启动 `launch/origincar_bringup.launch.py`
- `origincar_base/launch/origincar_bringup.launch.py` 会包含 `base_serial.launch.py`、`robot_mode_description.launch.py`（模型发布）、`imu_filter_madgwick_node` 和 EKF；`carto_slam:=true` 时跳过 EKF
- `lslidar_driver`：雷达可执行文件 `lslidar_driver_node`；N10 串口启动 `launch/lsn10_launch.py` 使用 `params/lidar_uart_ros2/lsn10.yaml`
- `origincar_slam/launch/slam.launch.py` 直接拉起雷达、`origincar_base` bringup、`slam_toolbox` 和默认开启的 `teleop_twist_keyboard`；可用 `enable_teleop:=false` 关闭键盘节点
- `origincar_nav/launch/navigation.launch.py` 直接拉起底盘、雷达和 `nav2_bringup`，默认地图来自 `origincar_slam/map/map_v0.1.yaml`（注意不是 `map_test.yaml`），参数是 `origincar_nav/config/nav2_params.yaml`
- `origincar_description`：只包含 `urdf/` 和 `meshes/`，无 launch 目录；实际模型加载由 `origincar_base/launch/robot_mode_description.launch.py` 完成，入口 xacro 是 `urdf/origincar.xacro`
- `origincar_description/urdf/origincar_stl.xacro` 是独立的 STL 网格模型文件（使用真实 STL mesh），与 `origincar.xacro`（使用几何体）是两套独立模型，目前 launch 加载的是 `origincar.xacro`
- `origincar_qr`：二维码扫描包，C++ 节点 `qr_scanner_node`（libzbar）和 Python 节点 `qr_scanner_py_node`（pyzbar + cv2 兜底），详见 `src/origincar/origincar_qr/AGENTS.md`
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

## Git 环境
- 全局 Git 身份：`user.name=yznn007`，`user.email=3181666393@qq.com`；提交前按项目要求确认身份
