from setuptools import setup
from glob import glob
import os

package_name = 'rov_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=[],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ROV',
    maintainer_email='rov@rov',
    description='BlueROV2 bringup launch files',
    license='MIT',
    entry_points={},
)
