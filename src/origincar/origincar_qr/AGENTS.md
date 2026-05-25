# AGENTS.md — origincar_qr

## 概述
`origincar_qr` 是一个 ROS 2 包，同时提供 **C++ (libzbar)** 和 **Python (OpenCV QRCodeDetector)** 两种二维码扫描节点。启动后打开 USB 摄像头，循环扫描画面中的二维码，将识别到的内容打印到标准输出。

## 包结构
```
origincar_qr/
├── AGENTS.md
├── CMakeLists.txt
├── package.xml
├── src/
│   └── qr_scanner_node.cpp        ← C++ 节点源码
├── origincar_qr/                   ← Python 模块
│   ├── __init__.py
│   └── qr_scanner_py_node.py
├── scripts/
│   └── qr_scanner_py_node         ← Python 可执行入口
├── launch/
│   ├── qr_scanner_cpp.launch.py   ← 启动 C++ 节点
│   └── qr_scanner_py.launch.py    ← 启动 Python 节点
```

## 依赖
| 依赖 | 用途 | 属于 |
|---|---|---|
| `rclcpp` | C++ 节点框架 | C++ |
| `libopencv-dev` | C++ 摄像头采集 + 预览窗口 | C++ |
| `libzbar-dev` | C++ QR 码解码 | C++ |
| `ament_cmake_python` | 安装 Python 模块 | 构建 |
| `rclpy` | Python 节点框架 | Python |
| `opencv-python` (pip) | Python 摄像头 + QR 解码 + 预览 | Python |

Python 节点额外需要 `pip install opencv-python`（如果未随 ROS 安装）。

## 参数（两节点共用）
| 参数名 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `camera_id` | int | 0 | 摄像头设备索引 `/dev/videoN` |
| `frame_width` | int | 640 | 摄像头采集分辨率宽 |
| `frame_height` | int | 480 | 摄像头采集分辨率高 |
| `scan_rate_hz` | double | 10.0 | 扫描循环频率 (Hz) |
| `show_preview` | bool | false | 是否显示 OpenCV 预览窗口 |

## 启动
```bash
# C++ 版（libzbar）
ros2 launch origincar_qr qr_scanner_cpp.launch.py
ros2 launch origincar_qr qr_scanner_cpp.launch.py camera_id:=1 show_preview:=true

# Python 版（cv2.QRCodeDetector）
ros2 launch origincar_qr qr_scanner_py.launch.py
ros2 launch origincar_qr qr_scanner_py.launch.py camera_id:=2 show_preview:=true

# 直接运行
ros2 run origincar_qr qr_scanner_node           # C++
ros2 run origincar_qr qr_scanner_py_node        # Python
```

## 构建
```bash
# 安装系统依赖
sudo apt install libopencv-dev libzbar-dev

# 编译
source /opt/ros/humble/setup.bash
colcon build --symlink-install --base-paths src/origincar --packages-select origincar_qr
source install/setup.bash
```

## 两个节点对比
| | C++ (qr_scanner_node) | Python (qr_scanner_py_node) |
|---|---|---|
| QR 解码库 | libzbar | cv2.QRCodeDetector |
| 系统依赖 | libopencv-dev, libzbar-dev | opencv-python (pip) |
| 启动文件 | `qr_scanner_cpp.launch.py` | `qr_scanner_py.launch.py` |
| ros2 run | `origincar_qr qr_scanner_node` | `origincar_qr qr_scanner_py_node` |
