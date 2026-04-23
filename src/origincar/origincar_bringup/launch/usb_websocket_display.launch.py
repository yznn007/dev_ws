import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch_ros.actions import Node
from launch.substitutions import TextSubstitution, LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python import get_package_share_directory, get_package_prefix

def generate_launch_description():
    # 获取包路径
    dnn_example_dir = get_package_share_directory('dnn_node_example')
    usb_cam_dir = get_package_share_directory('hobot_usb_cam')
    codec_dir = get_package_share_directory('hobot_codec')
    web_dir = get_package_share_directory('websocket')

    # 声明 Launch 参数 (Launch Arguments)
    dnn_example_config_file_arg = DeclareLaunchArgument(
        "dnn_example_config_file", 
        default_value=os.path.join(dnn_example_dir, "config/fcosworkconfig.json")
    )
    
    device_arg = DeclareLaunchArgument(
        'device', 
        default_value='/dev/video0', 
        description='USB camera device path'
    )

    # 1. USB 摄像头节点
    usb_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(usb_cam_dir, 'launch/hobot_usb_cam.launch.py')),
        launch_arguments={
            'usb_image_width': '640',
            'usb_image_height': '480',
            'usb_video_device': LaunchConfiguration('device')
        }.items()
    )

    # 2. 解码节点 (ROS Topic -> Shared Memory)
    nv12_codec_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(codec_dir, 'launch/hobot_codec_decode.launch.py')),
        launch_arguments={
            'codec_in_mode': 'ros',
            'codec_out_mode': 'shared_mem',
            'codec_sub_topic': '/image',
            'codec_pub_topic': '/hbmem_img'
        }.items()
    )

    # 3. 算法推理节点 (DNN Node)
    dnn_node_example_node = Node(
        package='dnn_node_example',
        executable='example',
        output='screen',
        parameters=[
#            {"config_file": LaunchConfiguration('dnn_example_config_file')},
            {"feed_type": 1}, # 1 代表使用订阅模式
            {"is_shared_mem_sub": 1}, # 开启共享内存订阅 (Zero-copy)
            {"msg_pub_topic_name": "hobot_dnn_detection"}
        ],
        arguments=['--ros-args', '--log-level', 'warn']
    )

    # 4. WebSocket 可视化节点
    web_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(web_dir, 'launch/websocket.launch.py')),
        launch_arguments={
            'websocket_image_topic': '/image',
            'websocket_image_type': 'mjpeg',
            'websocket_smart_topic': 'hobot_dnn_detection'
        }.items()
    )

    return LaunchDescription([
        dnn_example_config_file_arg,
        device_arg,
        usb_node,
        nv12_codec_node,
        dnn_node_example_node,
        web_node
    ])