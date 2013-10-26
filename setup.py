#!/usr/bin/env python
import distutils
import os
from distutils.core import setup
from distutils import sysconfig

data_dir = os.path.join(sysconfig.get_python_lib(), "hamster", "data")

required_packages = [
    "Beaker",
    "requests",
]

setup(name='hamster-sqlite',
      version='0.3',
      description='Minimal dependency nicely abstracted sqlite backend of hamster time tracker - lets you connect to your hamster db and do stuff in python',
      author='Toms Baugis',
      author_email='toms.baugis@gmail.com',
      url='https://github.com/projecthamster/hamster',
      package_dir = {'': 'src'},
      py_modules = ['hamster.storage', 'hamster.db', 'hamster.lib.__init__'],
      data_files=[(data_dir, ['data/hamster.db'])],
      install_requires=required_packages,
     )
