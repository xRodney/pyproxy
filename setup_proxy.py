from setuptools import setup, find_packages

import proxycore

setup(
    name="http-proxy",
    version=proxycore.PYPROXY_VERSION,
    description="HTTP reverse proxy for debugging and packet manipulation - Core and CLI",
    author="Dusan Jakub",
    maintainer="Dusan Jakub",
    packages=find_packages(include=['proxycore', 'proxycore.*']),
    py_modules=["setup", "setup_proxy"],
    install_requires=[
        "six", "PyHamcrest", "suds-sw==0.4.3"
    ],
    url="https://github.com/xRodney/pyproxy",
    entry_points={
        'console_scripts': [
            'http-proxy = proxy.pipe.apipe:main'
        ]
    }
)
