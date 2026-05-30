# OriginCar ROS 2 

## 项目简介

OriginCar 是一套面向全国大学生智能车竞赛（智慧医疗机器人创意赛）的 ROS 2 机器人软件平台。

### 核心功能

- 🚗 **底盘驱动**：支持差速/阿克曼双模式切换，串口通信，IMU 数据采集与 EKF 航迹融合
- 📡 **激光雷达感知**：雷神 LSN10 系列驱动，串口通信模式
- 🗺️ **SLAM 同步建图**：基于 SLAM Toolbox 异步建图，支持回环检测与交互式位姿修正
- 🧭 **自主导航**：Hybrid A* 全局规划 + TEB 局部规划，阿克曼运动学约束，动态避障
- 📷 **二维码识别**：C++/Python 双实现，多级预处理管线，远距离识别优化
- 🤖 **视觉 AI 推理**：RDK X5 平台 YOLOv5/EfficientDet 等 DNN 模型推理，WebSocket 实时可视化

## 项目文档

[详细文档](docs/details.md) - 工作空间结构、包说明、话题与坐标系、关键配置、常见故障排查

## 快速开始

### 环境要求

#### 硬件

- **上位机**：RDK X5
- **底盘**：OriginCar 
- **雷达**：镭神 N10 (雷达的驱动安装和 dev 别名设置请参考 n10 官方的文档)
- **摄像头**：USB 摄像头

#### 软件
- **操作系统**：Ubuntu 22.04

- **ROS 2**：Humble

- **编程语言**：Python 3.10 / C++17

### 获取源码

```bash
# 推荐克隆到用户根目录
cd ~
# 克隆仓库到本地
git clone https://github.com/yznn007/dev_ws.git
```

### 硬件驱动

#### 雷达

##### CH9102 驱动安装

```
wget https://www.wch.cn/downloads/file/65.html -O ch343ser.zip
unzip ch343ser.zip
cd ch343ser
sudo ./ch343ser_install.sh
```

##### 设置别名

[udev 使用教程](docs/udev.md) - 串口配置、设备别名

### 安装依赖

```bash
# 推荐使用 鱼香 ROS 一键安装 ROS 和 rosdepc：
source <(wget -qO- http://fishros.com/install)

 # 系统依赖
sudo apt update && sudo apt install -y \
  python3-colcon-common-extensions \
  libpcap-dev libpcl-dev libopencv-dev libzbar-dev

# ROS 包依赖
# rosdepc
sudo rosdepc init && rosdepc update
rosdepc install --from-paths src/origincar --ignore-src -r -y
# rosdep
# sudo rosdep init && rosdep update
# rosdep install --from-paths src/origincar --ignore-src -r -y

# Python 依赖
pip install opencv-python pyzbar
```

### 构建与环境加载

```bash
cd ~/dev_ws
colcon build --symlink-install --base-paths src/origincar
source ~/dev_ws/install/setup.bash
```

可选：写入 `~/.bashrc`。

```bash
echo "source ~/dev_ws/install/setup.bash" >> ~/.bashrc
```

## 启动

执行前先加载环境：(写入 .bashrc 可省略)

```bash
source ~/dev_ws/install/setup.bash
```

### 底盘启动

```bash
ros2 launch origincar_base origincar_bringup.launch.py
```

仅启动底盘串口节点：

```bash
ros2 launch origincar_base base_serial.launch.py akmcar:=false
```

### 雷达启动

```bash
ros2 launch lslidar_driver lsn10_launch.py
```

### SLAM 建图启动

```bash
ros2 launch origincar_slam slam.launch.py
```

如不需要键盘控制：

```bash
ros2 launch origincar_slam slam.launch.py enable_teleop:=false
```

### 地图保存(地图名称可自定义，修改 default_map 即可)

```bash
ros2 run nav2_map_server map_saver_cli -f ~/dev_ws/src/origincar/origincar_slam/map/default_map
```

### 导航启动

```bash
ros2 launch origincar_nav navigation.launch.py
```

## 命令速查

```bash
# SSH 连接(这里的ip是作者网络下的，请修改为你自己的)
ssh -Y sunrise@192.168.31.181

# 进入工作空间
cd ~/dev_ws

# 加载 ROS 环境
source /opt/ros/humble/setup.bash

# 删除构建产物
rm -rf build/ install/ log/

# 构建所有功能包
colcon build --symlink-install --base-paths src/origincar

# 构建单个功能包及依赖
colcon build --symlink-install --base-paths src/origincar --packages-up-to <功能包>

# 构建后加载 overlay
source ~/dev_ws/install/setup.bash

# 查看包
colcon list --base-paths src/origincar

# 查看节点与话题
ros2 node list
ros2 topic list

# 检查 N10 激光雷达硬件设备
ll /dev | grep ttyCH343USB*

# 底盘节点
ros2 launch origincar_base origincar_bringup.launch.py

# 键盘控制节点
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# 建图节点
ros2 launch origincar_slam slam.launch.py

# 导航节点
ros2 launch origincar_nav navigation.launch.py

# 摄像头节点
ros2 launch origincar_bringup usb_websocket_display.launch.py
# 预览：http://192.168.31.181:8000

# 地图保存(地图名称可自定义，修改 default_map 为你想要的名称即可)
ros2 run nav2_map_server map_saver_cli -f ~/dev_ws/src/origincar/origincar_slam/map/default_map

# 调试命令
ros2 topic echo /ackermann_cmd    # 查看转向角
ros2 topic echo /cmd_vel          # 查看 TEB 输出
ros2 topic echo /odom_combined    # 查看里程计
ros2 topic echo /local_plan       # 查看局部路径
ros2 run tf2_tools view_frames    # 检查 TF 树
```
