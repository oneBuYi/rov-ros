from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'rov_grid'
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
    description='Pool wall grid monitoring for ROV inspection',
    license='MIT',
    entry_points={
        'console_scripts': [
            'grid_monitor_node = rov_grid.grid_monitor_node:main',
        ],
    },
)
