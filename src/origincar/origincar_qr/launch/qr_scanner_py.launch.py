from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'camera_id', default_value='0',
            description='USB camera device index (/dev/videoN)'),
        DeclareLaunchArgument(
            'frame_width', default_value='640',
            description='Camera capture width'),
        DeclareLaunchArgument(
            'frame_height', default_value='480',
            description='Camera capture height'),
        DeclareLaunchArgument(
            'scan_rate_hz', default_value='10.0',
            description='QR scan loop rate (Hz)'),
        DeclareLaunchArgument(
            'show_preview', default_value='false',
            description='Show camera preview window (true/false)'),

        Node(
            package='origincar_qr',
            executable='qr_scanner_py_node',
            name='qr_scanner_node',
            output='screen',
            emulate_tty=True,
            parameters=[{
                'camera_id': LaunchConfiguration('camera_id'),
                'frame_width': LaunchConfiguration('frame_width'),
                'frame_height': LaunchConfiguration('frame_height'),
                'scan_rate_hz': LaunchConfiguration('scan_rate_hz'),
                'show_preview': LaunchConfiguration('show_preview'),
            }],
        ),
    ])
