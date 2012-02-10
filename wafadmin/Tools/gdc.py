#! /usr/bin/env python
# encoding: utf-8

import sys
import Utils,ar
from Configure import conftest
def find_gdc(conf):
	conf.find_program('gdc',var='D_COMPILER',mandatory=True)
def common_flags_gdc(conf):
	v=conf.env
	v['DFLAGS']=[]
	v['D_SRC_F']=''
	v['D_TGT_F']=['-c','-o','']
	v['DPATH_ST']='-I%s'
	v['D_LINKER']=v['D_COMPILER']
	v['DLNK_SRC_F']=''
	v['DLNK_TGT_F']=['-o','']
	v['DLIB_ST']='-l%s'
	v['DLIBPATH_ST']='-L%s'
	v['DLINKFLAGS']=[]
	v['DFLAGS_OPTIMIZED']=['-O3']
	v['DFLAGS_DEBUG']=['-O0']
	v['DFLAGS_ULTRADEBUG']=['-O0']
	v['D_shlib_DFLAGS']=[]
	v['D_shlib_LINKFLAGS']=['-shared']
	v['DHEADER_ext']='.di'
	v['D_HDR_F']='-fintfc -fintfc-file='
def detect(conf):
	conf.find_gdc()
	conf.check_tool('ar')
	conf.check_tool('d')
	conf.common_flags_gdc()
	conf.d_platform_flags()

conftest(find_gdc)
conftest(common_flags_gdc)
