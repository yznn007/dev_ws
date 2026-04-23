import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    nav_pkg_dir = get_package_share_directory('origincar_nav')
    base_pkg_dir = get_package_share_directory('origincar_base')
    slam_pkg_dir = get_package_share_directory('origincar_slam')
    lidar_pkg_dir = get_package_share_directory('lslidar_driver')
    nav2_pkg_dir = get_package_share_directory('nav2_bringup')

    default_map = os.path.join(slam_pkg_dir, 'map', 'map.yaml')
    default_params = os.path.join(nav_pkg_dir, 'config', 'nav2_params.yaml')
    default_bt_nav_to_pose = os.path.join(
        nav_pkg_dir,
        'behavior_trees',
        'navigate_to_pose_ackermann.xml'
    )
    lidar_config = os.path.join(
        lidar_pkg_dir,
        'params',
        'lidar_uart_ros2',
        'lsn10.yaml'
    )

    use_sim_time = LaunchConfiguration('use_sim_time')
    map_yaml = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')
    autostart = LaunchConfiguration('autostart')
    use_composition = LaunchConfiguration('use_composition')
    log_level = LaunchConfiguration('log_level')
    bt_nav_to_pose_xml = LaunchConfiguration('bt_nav_to_pose_xml')

    base_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(base_pkg_dir, 'launch', 'origincar_bringup.launch.py')
        ),
    )

    lidar_node = Node(
        package='lslidar_driver',
        executable='lslidar_driver_node',
        name='lslidar_driver_node',
        output='screen',
        parameters=[lidar_config],
    )

    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_pkg_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'slam': 'False',
            'map': map_yaml,
            'use_sim_time': use_sim_time,
            'params_file': params_file,
            'default_nav_to_pose_bt_xml': bt_nav_to_pose_xml,
            'autostart': autostart,
            'use_composition': use_composition,
            'log_level': log_level,
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'map',
            default_value=default_map,
            description='Absolute path to map yaml file',
        ),
        DeclareLaunchArgument(
            'params_file',
            default_value=default_params,
            description='Absolute path to nav2 parameter file',
        ),
        DeclareLaunchArgument(
            'bt_nav_to_pose_xml',
            default_value=default_bt_nav_to_pose,
            description='Absolute path to NavigateToPose BT xml',
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation clock if true',
        ),
        DeclareLaunchArgument(
            'autostart',
            default_value='true',
            description='Automatically startup nav2 lifecycle nodes',
        ),
        DeclareLaunchArgument(
            'use_composition',
            default_value='False',
            description='Launch nav2 in composition mode',
        ),
        DeclareLaunchArgument(
            'log_level',
            default_value='info',
            description='Nav2 log level',
        ),
        base_bringup,
        lidar_node,
        nav2_bringup,
    ])
