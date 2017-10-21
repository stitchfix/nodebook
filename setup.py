from __future__ import absolute_import
from setuptools import setup, find_packages
import os
import sys

setup(
    name='nodebook',
    version='0.2.1',
    author='Kevin Zielnicki',
    author_email='kzielnicki@stitchfix.com',
    license='Stitch Fix 2017',
    description='Nodebook Jupyter Extension',
    packages=find_packages(),
    long_description='Nodebook Jupyter Extension',
    url='https://github.com/stitchfix/nodebook',
    install_requires=[
        'ipython',
        'jupyter',
        'click',
        'dill',
        'msgpack-python',
        'pandas',
        'pytest-runner',
    ],
    tests_require=['pytest'],
    package_data={
        'nodebook': ['ipython/nbextensions/*.js']
    },
)
