#!/usr/bin/env python
"""
Commands to upload to pypi:

python setup.py sdist bdist_wheel
twine upload dist/*
"""
from setuptools import setup, find_packages
from distutils.core import Command
from setuptools.command.install import install
import platform
import os
import sys

__version__ = '0.0.6'

with open('README.rst') as readme:
    LONG_DESCRIPTION = readme.read()

entry_points = """
[console_scripts]
pygalvo = GalvoController.galvoController:main
"""

setup_requires = ['numpy', 'scipy']

# must have numpy and scipy installed already
install_requires = [
      'pydaqmx',
      'matplotlib>=1.4',
      'pyqtgraph>=0.9',
      'qtpy>=1.1',
      'setuptools>=1.0']



setup(name='GalvoController',
      version=__version__,
      description='2D Galvonmeter laser control system with NIDAQ USB 6001 device',
      long_description=LONG_DESCRIPTION,
      author='Brett Settle',
      author_email='brettjsettle@gmail.com',
      setup_requires=setup_requires,
      install_requires=install_requires,
      license='MIT',
      classifiers=[
          'Intended Audience :: Science/Research',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Topic :: Scientific/Engineering :: Visualization',
          ],
      packages=find_packages(),
      entry_points=entry_points,
      include_package_data=True,
      package_data={'gui': ['*.ui'],
                    'images': ['*.ico', '*.png', '*.jpg', '*.pdf']})









