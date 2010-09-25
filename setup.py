#!/usr/bin/env python
try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(name = 'socket-tornad.io',
    version = '0.1',
    description = 'Implementation of the socket.io protocol for Tornado.',
    author = 'Brendan W. McAdams',
    author_email = 'bmcadams@novus.com',
    url = 'http://novus.com',
    install_requires=[
      "pyCLI>=1.1.1",
      "simplejson",
      "unidecode",
      "tornado>=1.1.0",
      "twisted",
    ],
    #scripts = ['path/to/script']
)
