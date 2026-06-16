from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'rov_control'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='user',
    maintainer_email='user@example.com',
    description='BlueROV2 control nodes',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'depth_ctrl = rov_control.depth_ctrl_node:main',
            'adhesion = rov_control.adhesion_ctrl_node:main',
        ],
    },
)
