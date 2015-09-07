from distutils.core import setup

setup(
    name='httpload',
    version='0.0.1',
    packages=['httpload'],
    package_dir={'': 'src'},
    url='https://github.com/TargetHolding/httpload',
    license='Apache License 2.0',
    description=
    	'A straightforward python tool to generate some HTTP load with '
    	'connections kept alive and _not_ shared between clients.',
    install_requires=['aiohttp>=0.17.3', 'isodate>=0.5.4', ]
)
