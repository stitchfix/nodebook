from setuptools import setup, find_packages
import os
import sys

# we don't support wheels because they won't let us install the nbextension (a bit hacky)
if 'bdist_wheel' in sys.argv:
    raise RuntimeError("Nodebook does not support wheels, coercing to pip fallback behavior (non-fatal error)")

setup(
    name='nodebook',
    version='0.1.0',
    author='Kevin Zielnicki',
    author_email='kzielnicki@stitchfix.com',
    license='Stitch Fix 2017',
    description='Nodebook Jupyter Extension',
    packages=find_packages(),
    long_description='Nodebook Jupyter Extension',
    url='https://github.com/stitchfix/nodebook',
    install_requires=[
        'ipython<6',  # newer versions of ipython do not support 2.7
        'jupyter',
        'click',
        'dill',
        'msgpack-python',
        'pandas',
        'pytest-runner',
    ],
    tests_require=['pytest'],
    data_files=[
        (os.path.expanduser('~/.ipython/nbextensions'), ['ipython/nbextensions/nodebookext.js']),
        (os.path.expanduser('~/.ipython/extensions'), ['ipython/extensions/nodebookext.py']),
    ],
)
