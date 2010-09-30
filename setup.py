try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages


setup(
    name='SocketTornad.IO',
    version='0.1.0',
    author='Brendan W. McAdams',
    author_email='bmcadams@novus.com',
    packages=['tornad_io'],
    scripts=[],
    url='http://pypi.python.org/pypi/SocketTornad.IO/',
    license='LICENSE',
    description='Python implementation of the Socket.IO protocol for the Tornado webserver/framework.',
    long_description=open('README').read(),
    install_requires=[
        'pyCLI >= 1.1.1',
        'simplejson >= 2.1.0', # Decimal support
        'tornado >= 1.1.0',
        'beaker >= 1.5.3'
    ]
)
