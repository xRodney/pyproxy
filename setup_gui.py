from setuptools import setup, find_packages

import proxycore

setup(
    name="http-proxy-gui",
    version=proxycore.PYPROXY_VERSION,
    description="HTTP reverse proxy for debugging and packet manipulation - GUI",
    author="Dusan Jakub",
    maintainer="Dusan Jakub",
    packages=find_packages(include=['proxygui', 'proxygui.*']),
    py_modules=["setup", "setup_gui", "proxycore.__init__"],
    install_requires=[
        "http-proxy==" + str(proxycore.PYPROXY_VERSION),
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
