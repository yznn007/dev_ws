import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    # 1. 获取 URDF 文件的绝对路径
    urdf_file = os.path.join(
        get_package_share_directory('origincar_description'),
        'urdf',
        'origincar.urdf'
    )

    # 2. 读取 URDF 文件内容（必须是字符串形式）
    with open(urdf_file, 'r') as infp:
        robot_description_content = infp.read()

    # 3. 机器人状态发布者：将 URDF 发布到 /robot_description 话题并维护 TF 树
    # 
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description_content,
            'use_sim_time': False,
            'publish_frequency': 50.0  
        }]
    )

    # 4. 关节状态发布者：发布非固定关节（如轮子、舵机）的状态
    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        parameters=[{
            'robot_description': robot_description_content, 
            'use_sim_time': False
        }]
    )   

    ld = LaunchDescription()
    ld.add_action(robot_state_publisher_node)
    ld.add_action(joint_state_publisher_node)
    
    return ld