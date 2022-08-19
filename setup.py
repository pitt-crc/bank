"""Package installation logic"""

import re
from pathlib import Path

from setuptools import find_packages, setup

CURRENT_DIR = Path(__file__).resolve().parent
PACKAGE_REQUIREMENTS = CURRENT_DIR / 'requirements.txt'
DOCUMENTATION_REQUIREMENTS = CURRENT_DIR / 'docs' / 'requirements.txt'
INIT_PATH = CURRENT_DIR / 'bank' / '__init__.py'
README_PATH = CURRENT_DIR / 'README.md'


def get_long_description(readme_file=README_PATH):
    """Return a long description of tha parent package"""

    return readme_file.read_text()


def get_requirements(path):
    """Return a list of package dependencies"""

    with path.open() as req_file:
        return req_file.read().splitlines()


def get_init_variable(variable, init_path=INIT_PATH):
    """Return package version from the init file"""

    init_text = init_path.read_text()
    version_regex = re.compile(f"{variable} = '(.*?)'")
    return version_regex.findall(init_text)[0]


setup(
    name='crc-bank',
    description='Banking application for resource allocation in Slurm based HPC systems.',
    version=get_init_variable('__version__'),
    packages=find_packages(),
    python_requires='>=3.7',
    entry_points="""
        [console_scripts]
        crc-bank=bank.cli:CommandLineApplication.execute
    """,
    install_requires=get_requirements(PACKAGE_REQUIREMENTS),
    extras_require={
        'docs': get_requirements(DOCUMENTATION_REQUIREMENTS),
        'tests': ['coverage'],
    },
    author=get_init_variable('__author__'),
    keywords='pitt,crc,hpc,banking,slurm',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    license=get_init_variable('__license__'),
    classifiers=[
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering',
        'Topic :: System :: Systems Administration'
    ]
)
