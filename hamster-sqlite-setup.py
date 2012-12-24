#!/usr/bin/env python
from distutils.core import setup
import os
import distutils

data_dir = os.path.join(distutils.sysconfig.get_python_lib(), "hamster", "data")

setup(name='hamster-sqlite',
      version='0.1',
      description='Just the sqlite backend for hamster time tracker',
      author='Toms Baugis',
      author_email='toms.baugis@gmail.com',
      url='https://github.com/projecthamster/hamster',
      package_dir = {'': 'src'},
      py_modules = ['hamster.storage', 'hamster.db', 'hamster.lib.__init__'],
      data_files=[(data_dir, ['data/hamster.db'])],
     )
