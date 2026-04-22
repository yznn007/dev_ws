from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')
    save_map_timeout = LaunchConfiguration('save_map_timeout')
    free_thresh_default = LaunchConfiguration('free_thresh_default')
    occupied_thresh_default = LaunchConfiguration('occupied_thresh_default')

    map_saver_server = Node(
        package='nav2_map_server',
        executable='map_saver_server',
        name='map_saver',
        output='screen',
        emulate_tty=True,
        parameters=[
            {'use_sim_time': ParameterValue(use_sim_time, value_type=bool)},
            {'save_map_timeout': ParameterValue(save_map_timeout, value_type=float)},
            {'free_thresh_default': ParameterValue(free_thresh_default, value_type=float)},
            {'occupied_thresh_default': ParameterValue(occupied_thresh_default, value_type=float)},
        ],
    )

    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_map_saver',
        output='screen',
        emulate_tty=True,
        parameters=[
            {'use_sim_time': ParameterValue(use_sim_time, value_type=bool)},
            {'autostart': ParameterValue(autostart, value_type=bool)},
            {'node_names': ['map_saver']},
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation clock time',
        ),
        DeclareLaunchArgument(
            'autostart',
            default_value='true',
            description='Automatically activate map_saver lifecycle node',
        ),
        DeclareLaunchArgument(
            'save_map_timeout',
            default_value='5.0',
            description='Timeout in seconds when saving map',
        ),
        DeclareLaunchArgument(
            'free_thresh_default',
            default_value='0.25',
            description='Default free threshold',
        ),
        DeclareLaunchArgument(
            'occupied_thresh_default',
            default_value='0.65',
            description='Default occupied threshold',
        ),
        map_saver_server,
        lifecycle_manager,
    ])
