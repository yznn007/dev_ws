# udev 使用教程

## 什么是 udev

udev 是 Linux 的设备管理器，负责在系统启动时创建设备节点，并在设备插拔时动态管理设备。

**作用**：

- 为 USB 串口设备设置固定别名（如 `/dev/wheeltec_lidar`）
- 设置设备权限（如允许普通用户访问串口）
- 在设备插拔时执行自定义脚本

## 查看设备信息

### 1. 查看串口设备
```bash
# 查看所有串口设备
ls -l /dev/ttyUSB* /dev/ttyCH343USB*/dev/ttyACM*

# 查看 wheeltec 设备
ls -l /dev/wheeltec_*

#通过插拔确认雷达的设备号
```

### 3. 获取设备详细信息
```bash
# 获取雷达设备属性（用于编写 udev 规则）
udevadm info -a -n /dev/ttyCH343USB*

# 获取设备属性（简化输出）
udevadm info /dev/ttyUSB0
```

## 编写 udev 脚本规则

```
cd ~/dev_ws/docs/lidar
nano wheeltec_udev.sh
```

### 规则语法

```
KERNEL=="ttyUSB*", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", ATTRS{serial}=="0001", MODE:="0777", GROUP:="dialout", SYMLINK+="wheeltec_lidar"
```

**字段说明**：
- `KERNEL=="ttyUSB*"`：匹配设备内核名称
- `ATTRS{idVendor}=="10c4"`：匹配 USB 厂商 ID
- `ATTRS{idProduct}=="ea60"`：匹配 USB 产品 ID
- `ATTRS{serial}=="0001"`：匹配设备序列号
- `MODE:="0777"`：设置设备权限
- `GROUP:="dialout"`：设置设备所属组
- `SYMLINK+="wheeltec_lidar"`：创建符号链接别名

### 项目中的规则示例

**雷达串口**（`wheeltec_lidar`）：
- CP2102 芯片：`serial=0001`
- CH9102 芯片（有驱动）：`serial=5B8E675475`
- CH9102 芯片（无驱动）：`serial=0001`

**底盘串口**（`wheeltec_controller`）：
- CP2102 芯片：`serial=0002`
- CH9102 芯片：`serial=0002`

使用脚本

```
sudo bash ~/dev_ws/docs/lidar/wheeltec_udev.sh
```

## 验证规则

```bash
# 检查规则文件
cat /etc/udev/rules.d/wheeltec_lidar.rules

# 检查设备别名
ls -l /dev/wheeltec_lidar
```



### 案例 1：设备不存在

**问题描述**：执行 `ls -l /dev/wheeltec_lidar` 提示 "No such file or directory"

**排查步骤**：

```bash
# 1. 检查设备是否存在
ls -l /dev/ttyUSB* /dev/ttyCH343USB* /dev/ttyACM*

# 2. 检查 USB 设备
lsusb | grep -E "10c4|1a86"

# 3. 检查 udev 规则文件
cat /etc/udev/rules.d/wheeltec_lidar.rules

# 4. 检查 udev 日志
journalctl -u udev | tail -20

# 5. 检查设备属性
udevadm info -a -n /dev/ttyUSB0
```

**解决方案**：

```bash
# 1. 重新安装 udev 规则
sudo bash src/origincar/wheeltec_udev.sh

# 2. 重启 udev 服务
sudo service udev reload
sudo service udev restart

# 3. 插拔设备

# 4. 验证设备别名
ls -l /dev/wheeltec_lidar
```

### 案例 2：权限不足

**问题描述**：打开串口提示 "Permission denied"

**排查步骤**：

```bash
# 1. 检查设备权限
ls -l /dev/wheeltec_lidar

# 2. 检查用户组
groups

# 3. 检查 dialout 组
getent group dialout
```

**解决方案**：

```bash
# 1. 添加用户到 dialout 组
sudo usermod -aG dialout $USER

# 2. 重新登录(可以重启电脑)

# 3. 验证用户组
groups

# 4. 测试访问
cat /dev/wheeltec_lidar
```

### 案例 3：设备号冲突

**问题描述**：多个设备使用相同的别名

**排查步骤**：

```bash
# 1. 检查所有规则文件
ls -l /etc/udev/rules.d/wheeltec_*

# 2. 检查规则内容
cat /etc/udev/rules.d/wheeltec_lidar*.rules

# 3. 检查设备属性
udevadm info -a -n /dev/ttyUSB0
```

**解决方案**：

```bash
# 1. 删除冲突的规则文件
sudo rm /etc/udev/rules.d/wheeltec_lidar3.rules

# 2. 重新加载规则
sudo service udev reload
sudo service udev restart

# 3. 插拔设备

# 4. 验证设备别名
ls -l /dev/wheeltec_lidar
```



## 常见问题

### 1. 设备别名不存在
**原因**：udev 规则未正确加载
**解决**：
```bash
sudo bash src/origincar/wheeltec_udev.sh
sudo service udev restart
# 插拔设备
```

### 2. 权限不足
**原因**：用户不在 `dialout` 组
**解决**：
```bash
sudo usermod -aG dialout $USER
# 重新登录
```

### 3. 设备号冲突
**原因**：多个规则匹配同一设备
**解决**：
```bash
# 检查规则文件
ls -l /etc/udev/rules.d/wheeltec_*

# 删除冲突的规则
sudo rm /etc/udev/rules.d/wheeltec_lidar3.rules

# 重新加载规则
sudo service udev restart
```

### 4. 驱动问题
**原因**：芯片驱动未安装
**解决**：
```bash
# 检查芯片型号
lsusb | grep -E "10c4|1a86"

# 安装对应驱动
# CP2102：内置驱动
# CH9102：需要安装驱动
```

## 参考资源

- ai
- 网店客服

- [udev Wiki](https://wiki.archlinux.org/title/udev)
- [udevadm Manual](https://man7.org/linux/man-pages/man8/udevadm.8.html)
- [USB ID Database](http://www.linux-usb.org/usb.ids)
- [CH9102 驱动下载](https://www.wch.cn/downloads/file/65.html)
