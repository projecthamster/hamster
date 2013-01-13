#!/usr/bin/env python
from distutils.core import setup
import os
import distutils

data_dir = os.path.join(distutils.sysconfig.get_python_lib(), "hamster", "data")

setup(name='hamster-sqlite',
      version='0.2',
      description='The sqlite backend of hamster time tracker (can be used as a good start for any front-end work)',
      author='Toms Baugis',
      author_email='toms.baugis@gmail.com',
      url='https://github.com/projecthamster/hamster',
      package_dir = {'': 'src'},
      py_modules = ['hamster.storage', 'hamster.db', 'hamster.lib.__init__'],
      data_files=[(data_dir, ['data/hamster.db'])],
     )
