#! /usr/bin/env python
# encoding: utf-8

import os,sys
import TaskGen,Utils,Utils,Runner,Options,Build
from Logs import debug,warn,info
from TaskGen import extension,taskgen,before,after,feature
from Configure import conf
EXT_PY=['.py']
FRAG_2='''
#include "Python.h"
#ifdef __cplusplus
extern "C" {
#endif
	void Py_Initialize(void);
	void Py_Finalize(void);
#ifdef __cplusplus
}
#endif
int main()
{
   Py_Initialize();
   Py_Finalize();
   return 0;
}
'''
def init_pyext(self):
	self.default_install_path='${PYTHONDIR}'
	self.uselib=self.to_list(getattr(self,'uselib',''))
	if not'PYEXT'in self.uselib:
		self.uselib.append('PYEXT')
	self.env['MACBUNDLE']=True
def pyext_shlib_ext(self):
	self.env['shlib_PATTERN']=self.env['pyext_PATTERN']
def init_pyembed(self):
	self.uselib=self.to_list(getattr(self,'uselib',''))
	if not'PYEMBED'in self.uselib:
		self.uselib.append('PYEMBED')
def process_py(self,node):
	if not(self.bld.is_install and self.install_path):
		return
	def inst_py(ctx):
		install_pyfile(self,node)
	self.bld.add_post_fun(inst_py)
def install_pyfile(self,node):
	path=self.bld.get_install_path(self.install_path+os.sep+node.name,self.env)
	self.bld.install_files(self.install_path,[node],self.env,self.chmod,postpone=False)
	if self.bld.is_install<0:
		info("* removing byte compiled python files")
		for x in'co':
			try:
				os.remove(path+x)
			except OSError:
				pass
	if self.bld.is_install>0:
		if self.env['PYC']or self.env['PYO']:
			info("* byte compiling %r"%path)
		if self.env['PYC']:
			program=("""
import sys, py_compile
for pyfile in sys.argv[1:]:
	py_compile.compile(pyfile, pyfile + 'c')
""")
			argv=[self.env['PYTHON'],'-c',program,path]
			ret=Utils.pproc.Popen(argv).wait()
			if ret:
				raise Utils.WafError('bytecode compilation failed %r'%path)
		if self.env['PYO']:
			program=("""
import sys, py_compile
for pyfile in sys.argv[1:]:
	py_compile.compile(pyfile, pyfile + 'o')
""")
			argv=[self.env['PYTHON'],self.env['PYFLAGS_OPT'],'-c',program,path]
			ret=Utils.pproc.Popen(argv).wait()
			if ret:
				raise Utils.WafError('bytecode compilation failed %r'%path)
class py_taskgen(TaskGen.task_gen):
	def __init__(self,*k,**kw):
		TaskGen.task_gen.__init__(self,*k,**kw)
def init_py(self):
	self.default_install_path='${PYTHONDIR}'
def _get_python_variables(python_exe,variables,imports=['import sys']):
	program=list(imports)
	program.append('')
	for v in variables:
		program.append("print(repr(%s))"%v)
	os_env=dict(os.environ)
	try:
		del os_env['MACOSX_DEPLOYMENT_TARGET']
	except KeyError:
		pass
	proc=Utils.pproc.Popen([python_exe,"-c",'\n'.join(program)],stdout=Utils.pproc.PIPE,env=os_env)
	output=proc.communicate()[0].split("\n")
	if proc.returncode:
		if Options.options.verbose:
			warn("Python program to extract python configuration variables failed:\n%s"%'\n'.join(["line %03i: %s"%(lineno+1,line)for lineno,line in enumerate(program)]))
		raise RuntimeError
	return_values=[]
	for s in output:
		s=s.strip()
		if not s:
			continue
		if s=='None':
			return_values.append(None)
		elif s[0]=="'"and s[-1]=="'":
			return_values.append(s[1:-1])
		elif s[0].isdigit():
			return_values.append(int(s))
		else:break
	return return_values
def check_python_headers(conf,mandatory=True):
	if not conf.env['CC_NAME']and not conf.env['CXX_NAME']:
		conf.fatal('load a compiler first (gcc, g++, ..)')
	if not conf.env['PYTHON_VERSION']:
		conf.check_python_version()
	env=conf.env
	python=env['PYTHON']
	if not python:
		conf.fatal('could not find the python executable')
	if Options.platform=='darwin':
		conf.check_tool('osx')
	try:
		v='prefix SO SYSLIBS LDFLAGS SHLIBS LIBDIR LIBPL INCLUDEPY Py_ENABLE_SHARED MACOSX_DEPLOYMENT_TARGET'.split()
		(python_prefix,python_SO,python_SYSLIBS,python_LDFLAGS,python_SHLIBS,python_LIBDIR,python_LIBPL,INCLUDEPY,Py_ENABLE_SHARED,python_MACOSX_DEPLOYMENT_TARGET)=_get_python_variables(python,["get_config_var('%s')"%x for x in v],['from distutils.sysconfig import get_config_var'])
	except RuntimeError:
		conf.fatal("Python development headers not found (-v for details).")
	conf.log.write("""Configuration returned from %r:
python_prefix = %r
python_SO = %r
python_SYSLIBS = %r
python_LDFLAGS = %r
python_SHLIBS = %r
python_LIBDIR = %r
python_LIBPL = %r
INCLUDEPY = %r
Py_ENABLE_SHARED = %r
MACOSX_DEPLOYMENT_TARGET = %r
"""%(python,python_prefix,python_SO,python_SYSLIBS,python_LDFLAGS,python_SHLIBS,python_LIBDIR,python_LIBPL,INCLUDEPY,Py_ENABLE_SHARED,python_MACOSX_DEPLOYMENT_TARGET))
	if python_MACOSX_DEPLOYMENT_TARGET:
		conf.env['MACOSX_DEPLOYMENT_TARGET']=python_MACOSX_DEPLOYMENT_TARGET
		conf.environ['MACOSX_DEPLOYMENT_TARGET']=python_MACOSX_DEPLOYMENT_TARGET
	env['pyext_PATTERN']='%s'+python_SO
	if python_SYSLIBS is not None:
		for lib in python_SYSLIBS.split():
			if lib.startswith('-l'):
				lib=lib[2:]
			env.append_value('LIB_PYEMBED',lib)
	if python_SHLIBS is not None:
		for lib in python_SHLIBS.split():
			if lib.startswith('-l'):
				env.append_value('LIB_PYEMBED',lib[2:])
			else:
				env.append_value('LINKFLAGS_PYEMBED',lib)
	if Options.platform!='darwin'and python_LDFLAGS:
		env.append_value('LINKFLAGS_PYEMBED',python_LDFLAGS.split())
	result=False
	name='python'+env['PYTHON_VERSION']
	if python_LIBDIR is not None:
		path=[python_LIBDIR]
		conf.log.write("\n\n# Trying LIBDIR: %r\n"%path)
		result=conf.check(lib=name,uselib='PYEMBED',libpath=path)
	if not result and python_LIBPL is not None:
		conf.log.write("\n\n# try again with -L$python_LIBPL (some systems don't install the python library in $prefix/lib)\n")
		path=[python_LIBPL]
		result=conf.check(lib=name,uselib='PYEMBED',libpath=path)
	if not result:
		conf.log.write("\n\n# try again with -L$prefix/libs, and pythonXY name rather than pythonX.Y (win32)\n")
		path=[os.path.join(python_prefix,"libs")]
		name='python'+env['PYTHON_VERSION'].replace('.','')
		result=conf.check(lib=name,uselib='PYEMBED',libpath=path)
	if result:
		env['LIBPATH_PYEMBED']=path
		env.append_value('LIB_PYEMBED',name)
	else:
		conf.log.write("\n\n### LIB NOT FOUND\n")
	if(sys.platform=='win32'or sys.platform.startswith('os2')or sys.platform=='darwin'or Py_ENABLE_SHARED):
		env['LIBPATH_PYEXT']=env['LIBPATH_PYEMBED']
		env['LIB_PYEXT']=env['LIB_PYEMBED']
	python_config=conf.find_program('python%s-config'%('.'.join(env['PYTHON_VERSION'].split('.')[:2])),var='PYTHON_CONFIG')
	if not python_config:
		python_config=conf.find_program('python-config-%s'%('.'.join(env['PYTHON_VERSION'].split('.')[:2])),var='PYTHON_CONFIG')
	includes=[]
	if python_config:
		for incstr in Utils.cmd_output("%s %s --includes"%(python,python_config)).strip().split():
			if(incstr.startswith('-I')or incstr.startswith('/I')):
				incstr=incstr[2:]
			if incstr not in includes:
				includes.append(incstr)
		conf.log.write("Include path for Python extensions ""(found via python-config --includes): %r\n"%(includes,))
		env['CPPPATH_PYEXT']=includes
		env['CPPPATH_PYEMBED']=includes
	else:
		conf.log.write("Include path for Python extensions ""(found via distutils module): %r\n"%(INCLUDEPY,))
		env['CPPPATH_PYEXT']=[INCLUDEPY]
		env['CPPPATH_PYEMBED']=[INCLUDEPY]
	if env['CC_NAME']=='gcc':
		env.append_value('CCFLAGS_PYEMBED','-fno-strict-aliasing')
		env.append_value('CCFLAGS_PYEXT','-fno-strict-aliasing')
	if env['CXX_NAME']=='gcc':
		env.append_value('CXXFLAGS_PYEMBED','-fno-strict-aliasing')
		env.append_value('CXXFLAGS_PYEXT','-fno-strict-aliasing')
	conf.check(define_name='HAVE_PYTHON_H',uselib='PYEMBED',fragment=FRAG_2,errmsg='Could not find the python development headers',mandatory=mandatory)
def check_python_version(conf,minver=None):
	assert minver is None or isinstance(minver,tuple)
	python=conf.env['PYTHON']
	if not python:
		conf.fatal('could not find the python executable')
	cmd=[python,"-c","import sys\nfor x in sys.version_info: print(str(x))"]
	debug('python: Running python command %r'%cmd)
	proc=Utils.pproc.Popen(cmd,stdout=Utils.pproc.PIPE)
	lines=proc.communicate()[0].split()
	assert len(lines)==5,"found %i lines, expected 5: %r"%(len(lines),lines)
	pyver_tuple=(int(lines[0]),int(lines[1]),int(lines[2]),lines[3],int(lines[4]))
	result=(minver is None)or(pyver_tuple>=minver)
	if result:
		pyver='.'.join([str(x)for x in pyver_tuple[:2]])
		conf.env['PYTHON_VERSION']=pyver
		if'PYTHONDIR'in conf.environ:
			pydir=conf.environ['PYTHONDIR']
		else:
			if sys.platform=='win32':
				(python_LIBDEST,pydir)=_get_python_variables(python,["get_config_var('LIBDEST')","get_python_lib(standard_lib=0, prefix=%r)"%conf.env['PREFIX']],['from distutils.sysconfig import get_config_var, get_python_lib'])
			else:
				python_LIBDEST=None
				(pydir,)=_get_python_variables(python,["get_python_lib(standard_lib=0, prefix=%r)"%conf.env['PREFIX']],['from distutils.sysconfig import get_config_var, get_python_lib'])
			if python_LIBDEST is None:
				if conf.env['LIBDIR']:
					python_LIBDEST=os.path.join(conf.env['LIBDIR'],"python"+pyver)
				else:
					python_LIBDEST=os.path.join(conf.env['PREFIX'],"lib","python"+pyver)
		if hasattr(conf,'define'):
			conf.define('PYTHONDIR',pydir)
		conf.env['PYTHONDIR']=pydir
	pyver_full='.'.join(map(str,pyver_tuple[:3]))
	if minver is None:
		conf.check_message_custom('Python version','',pyver_full)
	else:
		minver_str='.'.join(map(str,minver))
		conf.check_message('Python version',">= %s"%minver_str,result,option=pyver_full)
	if not result:
		conf.fatal('The python version is too old (%r)'%pyver_full)
def check_python_module(conf,module_name):
	result=not Utils.pproc.Popen([conf.env['PYTHON'],"-c","import %s"%module_name],stderr=Utils.pproc.PIPE,stdout=Utils.pproc.PIPE).wait()
	conf.check_message('Python module',module_name,result)
	if not result:
		conf.fatal('Could not find the python module %r'%module_name)
def detect(conf):
	if not conf.env.PYTHON:
		conf.env.PYTHON=sys.executable
	python=conf.find_program('python',var='PYTHON')
	if not python:
		conf.fatal('Could not find the path of the python executable')
	v=conf.env
	v['PYCMD']='"import sys, py_compile;py_compile.compile(sys.argv[1], sys.argv[2])"'
	v['PYFLAGS']=''
	v['PYFLAGS_OPT']='-O'
	v['PYC']=getattr(Options.options,'pyc',1)
	v['PYO']=getattr(Options.options,'pyo',1)
def set_options(opt):
	opt.add_option('--nopyc',action='store_false',default=1,help='Do not install bytecode compiled .pyc files (configuration) [Default:install]',dest='pyc')
	opt.add_option('--nopyo',action='store_false',default=1,help='Do not install optimised compiled .pyo files (configuration) [Default:install]',dest='pyo')

before('apply_incpaths','apply_lib_vars','apply_type_vars')(init_pyext)
feature('pyext')(init_pyext)
before('apply_bundle')(init_pyext)
before('apply_link','apply_lib_vars','apply_type_vars')(pyext_shlib_ext)
after('apply_bundle')(pyext_shlib_ext)
feature('pyext')(pyext_shlib_ext)
before('apply_incpaths','apply_lib_vars','apply_type_vars')(init_pyembed)
feature('pyembed')(init_pyembed)
extension(EXT_PY)(process_py)
before('apply_core')(init_py)
after('vars_target_cprogram','vars_target_cshlib')(init_py)
feature('py')(init_py)
conf(check_python_headers)
conf(check_python_version)
conf(check_python_module)
