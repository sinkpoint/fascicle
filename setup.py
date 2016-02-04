try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

#myreqs = parse_requirements('requirements.txt')

config = {
    'name': 'fascicle',
    'description': 'Tractography vtk sqlite manager',
    'author': 'David Qixiang Chen',
    'url': 'https://github.com/sinkpoint/fascicle',
    'download_url': 'https://github.com/sinkpoint/fascicle',
    'author_email': 'qixiang.chen@gmail.com',
    'version': '0.1',
    'install_requires': ['numpy', 'vtk', 'sqlalchemy'],
    'packages': ['fascicle'],
    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    'entry_points': {
        'console_scripts': [
            'fascicle=fascicle.trkmanage:main',
        ],
    },    
}

setup(**config)