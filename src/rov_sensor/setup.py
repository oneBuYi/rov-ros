from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'rov_sensor'
pkg_dir = os.path.dirname(__file__)

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'),
         glob(os.path.join(pkg_dir, 'config', '*.yaml'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='oneBuYi',
    maintainer_email='wanghaojiehero@qq.com',
    description='ROV sensor and camera publisher nodes',
    license='MIT',
    entry_points={
        'console_scripts': [
            'camera_pub_node = rov_sensor.camera_pub_node:main',
            'ugps_bridge_node = rov_sensor.ugps_bridge_node:main',
        ],
    },
)
