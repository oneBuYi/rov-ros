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
    maintainer='ROV',
    maintainer_email='rov@rov',
    description='BlueROV2 control nodes',
    license='MIT',
    entry_points={
        'console_scripts': [
            'depth_ctrl = rov_control.depth_ctrl_node:main',
            'adhesion = rov_control.adhesion_ctrl_node:main',
        ],
    },
)
