from setuptools import setup, find_packages

import proxy

setup(
    name="http-proxy-gui",
    version=proxy.__version__,
    description="HTTP reverse proxy for debugging and packet manipulation - GUI",
    author="Dusan Jakub",
    maintainer="Dusan Jakub",
    packages=find_packages(include=['proxygui', 'proxygui.*']),
    install_requires=[
        "hexdump==3.3",
        "PyQt5==5.8.2"
    ],
    url="https://github.com/xRodney/pyproxy",
    entry_points={
        'gui_scripts': [
            'http-proxy-gui = proxygui.main:main'
        ]
    }
)
