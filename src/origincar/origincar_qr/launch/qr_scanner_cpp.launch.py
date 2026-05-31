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
            'frame_width', default_value='0',
            description='Capture width (0 = auto-detect max)'),
        DeclareLaunchArgument(
            'frame_height', default_value='0',
            description='Capture height (0 = auto-detect max)'),
        DeclareLaunchArgument(
            'scan_rate_hz', default_value='10.0',
            description='QR scan loop rate (Hz)'),
        DeclareLaunchArgument(
            'show_preview', default_value='false',
            description='Show CLAHE preview window (true/false)'),
        DeclareLaunchArgument(
            'enable_multiscale', default_value='true',
            description='Enable multi-pass preprocessing '
                        '(CLAHE + binary + downscale pyramid)'),
        DeclareLaunchArgument(
            'clahe_clip_limit', default_value='2.0',
            description='CLAHE clip limit for contrast enhancement'),
        DeclareLaunchArgument(
            'clahe_tile_size', default_value='8',
            description='CLAHE tile grid size'),
        DeclareLaunchArgument(
            'use_raw', default_value='false',
            description='Skip all preprocessing, decode raw grayscale image'),
        DeclareLaunchArgument(
            'crop', default_value='1',
            description='Center crop factor: 1=full, 2=half, 3=1/3, ...'),

        Node(
            package='origincar_qr',
            executable='qr_scanner_node',
            name='qr_scanner_node',
            output='screen',
            emulate_tty=True,
            parameters=[{
                'camera_id': LaunchConfiguration('camera_id'),
                'frame_width': LaunchConfiguration('frame_width'),
                'frame_height': LaunchConfiguration('frame_height'),
                'scan_rate_hz': LaunchConfiguration('scan_rate_hz'),
                'show_preview': LaunchConfiguration('show_preview'),
                'enable_multiscale': LaunchConfiguration('enable_multiscale'),
                'clahe_clip_limit': LaunchConfiguration('clahe_clip_limit'),
                'clahe_tile_size': LaunchConfiguration('clahe_tile_size'),
                'use_raw': LaunchConfiguration('use_raw'),
                'crop': LaunchConfiguration('crop'),
            }],
        ),
    ])
