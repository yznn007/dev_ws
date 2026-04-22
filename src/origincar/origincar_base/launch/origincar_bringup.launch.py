import os
from pathlib import Path
import launch
from launch.actions import SetEnvironmentVariable
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, GroupAction,
                            IncludeLaunchDescription, SetEnvironmentVariable)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import PushRosNamespace
import launch_ros.actions
from launch.conditions import UnlessCondition

def generate_launch_description():
    # Get the launch directory
    bringup_dir = get_package_share_directory('origincar_base')
    launch_dir = os.path.join(bringup_dir, 'launch')
    ekf_config = Path(get_package_share_directory('origincar_base'), 'config', 'ekf.yaml')
    imu_config = Path(get_package_share_directory('origincar_base'), 'config', 'imu.yaml')

    
    carto_slam = LaunchConfiguration('carto_slam', default='false')
    carto_slam_dec = DeclareLaunchArgument('carto_slam',default_value='false')
            
    origincar_base = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(launch_dir, 'base_serial.launch.py')),
            launch_arguments={'akmcar': 'true'}.items(),
    )

    choose_car = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(launch_dir, 'robot_mode_description.launch.py')),
    )
#    tf = launch_ros.actions.Node(
#        package='tf2_ros',
#        executable='static_transform_publisher',
#        # x y z yaw pitch roll parent child
#        arguments=['0', '0', '0.1', '0', '0', '0', 'base_link', 'laser']
#    )
    
    imu_filter_node =  launch_ros.actions.Node(
        package='imu_filter_madgwick',
        executable='imu_filter_madgwick_node',
        parameters=[imu_config]
    )
    
    robot_ekf = launch_ros.actions.Node(
            condition=UnlessCondition(carto_slam),
            package='robot_localization', 
            executable='ekf_node', 
            parameters=[ekf_config,{'use_sim_time': False}],
            remappings=[("odometry/filtered", "odom_combined")]
            )
                              


    ld = LaunchDescription()

    ld.add_action(carto_slam_dec)
    ld.add_action(origincar_base)
    ld.add_action(choose_car)
#    ld.add_action(tf)
    ld.add_action(imu_filter_node)    
    ld.add_action(robot_ekf)

    return ld

