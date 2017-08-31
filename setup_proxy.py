from setuptools import setup, find_packages

import proxy

setup(
    name="pyproxy",
    version=proxy.__version__,
    description="HTTP reverse proxy for debugging and packet manipulation - Core and CLI",
    author="Dusan Jakub",
    maintainer="Dusan Jakub",
    packages=find_packages(include=['proxy.*']),
    install_requires=[
        "six", "PyHamcrest", "suds-sw==0.4.3"
    ],
    url="https://github.com/xRodney/pyproxy",
    entry_points={
        'console_scripts': [
            'pyproxy = proxy.pipe.apipe:main'
        ]
    }
)
