# AGENTS.md — origincar_qr

## 概述
`origincar_qr` 是一个 ROS 2 包，同时提供 **C++ (libzbar)** 和 **Python (pyzbar + cv2.QRCodeDetector)** 两种二维码扫描节点。启动后打开 USB 摄像头，循环扫描画面中的二维码，将识别到的内容打印到标准输出。

### 识别距离优化（v2）
从原始版本（30cm）大幅提升识别距离的关键改进：
1. **默认分辨率 640×480 → 1280×720** — 二维码模块获得更多像素
2. **CLAHE 对比度增强** — 解决光线不均、提升远处低对比度二维码的可检测性
3. **多级预处理管线**：CLAHE → CLAHE+Sharpen → Adaptive Binary → CLAHE+Binary → 下采样金字塔
4. **Python 版改用 pyzbar**（底层 zbar，远距离优于 cv2.QRCodeDetector），cv2 仅作极端角度兜底
5. **MJPG 编码** — 高清分辨率下保持帧率

## 包结构
```
origincar_qr/
├── AGENTS.md
├── CMakeLists.txt
├── package.xml
├── src/
│   └── qr_scanner_node.cpp        ← C++ 节点源码（zbar + CLAHE）
├── origincar_qr/                   ← Python 模块
│   ├── __init__.py
│   └── qr_scanner_py_node.py      ← Python 节点（pyzbar + cv2 fallback）
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
| `libopencv-dev` | C++ 摄像头采集 + 预处理 + 预览 | C++ |
| `libzbar-dev` | C++ QR 码解码 | C++ |
| `ament_cmake_python` | 安装 Python 模块 | 构建 |
| `rclpy` | Python 节点框架 | Python |
| `opencv-python` (pip) | Python 摄像头 + 预处理 + 预览 | Python |
| `pyzbar` (pip) | Python QR 解码（主解码器） | Python |

Python 节点需要：
```bash
pip install opencv-python pyzbar
```

## 参数
| 参数名 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `camera_id` | int | 0 | 摄像头设备索引 `/dev/videoN` |
| `frame_width` | int | 1280 | 摄像头采集分辨率宽 |
| `frame_height` | int | 720 | 摄像头采集分辨率高 |
| `scan_rate_hz` | double | 10.0 | 扫描循环频率 (Hz) |
| `show_preview` | bool | false | 是否显示 OpenCV 预览窗口 |
| `enable_multiscale` | bool | true | 启用多级预处理（CLAHE/Sharpen/Binary/金字塔） |
| `use_raw` | bool | false | 跳过所有预处理，直接在原始灰度图上解码 |
| `crop` | int | 1 | 中心裁剪因子：1=全图，2=半幅，3=1/3，4=1/4，… |
| `clahe_clip_limit` | double | 2.0 | CLAHE 对比度限幅 |
| `clahe_tile_size` | int | 8 | CLAHE 网格尺寸 |

### 调参建议
- 如果摄像头不支持 720p，设置 `frame_width:=640 frame_height:=480`
- 如果 CPU 不足（树莓派等），关闭多级处理：`enable_multiscale:=false`
- 光照极差时提高 CLAHE：`clahe_clip_limit:=3.0 clahe_tile_size:=4`

## 解码管线
两个节点的解码策略相同（多 pass，任一命中即输出）：

| Pass | C++ 解码器 | Python 解码器 | 输入图像 |
|---|---|---|---|
| 1 | zbar | pyzbar | CLAHE 灰度 |
| 2 | zbar | pyzbar | CLAHE + Sharpen |
| 3 | zbar | pyzbar | Adaptive Binary |
| 4 | zbar | pyzbar | CLAHE + Binary |
| 5 | — | cv2.QRCodeDetector | 原始彩色（极端角度兜底） |
| 6–7 | zbar | pyzbar | CLAHE 0.75× / 0.5× 下采样 |

## 启动
```bash
# C++ 版（libzbar）
ros2 launch origincar_qr qr_scanner_cpp.launch.py
ros2 launch origincar_qr qr_scanner_cpp.launch.py camera_id:=1 show_preview:=true

# Python 版（pyzbar + cv2 fallback）
ros2 launch origincar_qr qr_scanner_py.launch.py
ros2 launch origincar_qr qr_scanner_py.launch.py camera_id:=2 show_preview:=true

# 低分辨率模式（摄像头不支持 720p 时）
ros2 launch origincar_qr qr_scanner_cpp.launch.py frame_width:=640 frame_height:=480

# 直接运行
ros2 run origincar_qr qr_scanner_node           # C++
ros2 run origincar_qr qr_scanner_py_node        # Python
```

## 构建
```bash
# 安装系统依赖
sudo apt install libopencv-dev libzbar-dev
pip install opencv-python pyzbar

# 编译
source /opt/ros/humble/setup.bash
colcon build --symlink-install --base-paths src/origincar --packages-select origincar_qr
source install/setup.bash
```

## 两个节点对比
| | C++ (qr_scanner_node) | Python (qr_scanner_py_node) |
|---|---|---|
| QR 解码库 | libzbar | pyzbar (zbar) + cv2.QRCodeDetector fallback |
| 系统依赖 | libopencv-dev, libzbar-dev | pyzbar (pip), opencv-python (pip) |
| 启动文件 | `qr_scanner_cpp.launch.py` | `qr_scanner_py.launch.py` |
| ros2 run | `origincar_qr qr_scanner_node` | `origincar_qr qr_scanner_py_node` |
| 远距离 | ★★★★ | ★★★★★ (pyzbar + cv2 双重) |
| 极端角度 | ★★★ | ★★★★ (cv2 fallback) |
