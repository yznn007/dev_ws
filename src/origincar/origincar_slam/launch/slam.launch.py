import os
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # 包名
    slam_pkg_name = 'origincar_slam'
    lidar_pkg_name = 'lslidar_driver'
    base_pkg_name = 'origincar_base'
    desc_pkg_name = 'origincar_description'

    # 配置文件路径
    lidar_config_path = os.path.join(
        get_package_share_directory(lidar_pkg_name),
        'params',
        'lidar_uart_ros2',
        'lsn10.yaml'
    )

    slam_config_path = os.path.join(
        get_package_share_directory(slam_pkg_name),
        'config',
        'slam_params.yaml'
    )

    # 底盘启动文件路径
    base_launch_dir = os.path.join(
        get_package_share_directory(base_pkg_name),
        'launch'
    )

    return LaunchDescription([
        # 声明启动参数
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation clock time'
        ),
        DeclareLaunchArgument(
            'enable_teleop',
            default_value='true',
            description='Launch keyboard teleop node'
        ),
        # ============ 激光雷达节点 ============
        Node(
            package=lidar_pkg_name,
            executable='lslidar_driver_node',
            name='lslidar_driver_node',
            output='screen',
            parameters=[lidar_config_path]
        ),
        # ============ 启动小车底盘 (origincar_base) ============
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(base_launch_dir, 'origincar_bringup.launch.py')
            ),
        ),

        # ============ SLAM Toolbox节点 (异步建图模式) ============
        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            output='screen',
            parameters=[slam_config_path]
        ),
        # ============ 键盘控制节点 ============
        Node(
            condition=IfCondition(LaunchConfiguration('enable_teleop')),
            package='teleop_twist_keyboard',
            executable='teleop_twist_keyboard',
            name='teleop_twist_keyboard',
            output='screen',
            emulate_tty=True,
            prefix='xterm -e'
        ),
    ])
