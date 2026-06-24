from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'rov_gcs'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='oneBuYi',
    maintainer_email='wanghaojiehero@qq.com',
    description='Web GCS backend',
    license='MIT',
    entry_points={
        'console_scripts': [
            'gcs_backend = rov_gcs.backend.main:main',
        ],
    },
)
