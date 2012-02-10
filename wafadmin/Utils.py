#! /usr/bin/env python
# encoding: utf-8

import os,sys,imp,string,errno,traceback,inspect,re,shutil,datetime,gc
try:from UserDict import UserDict
except ImportError:from collections import UserDict
if sys.hexversion>=0x2060000 or os.name=='java':
	import subprocess as pproc
else:
	import pproc
import Logs
from Constants import*
try:
	from collections import deque
except ImportError:
	class deque(list):
		def popleft(self):
			return self.pop(0)
is_win32=sys.platform=='win32'
try:
	from collections import defaultdict as DefaultDict
except ImportError:
	class DefaultDict(dict):
		def __init__(self,default_factory):
			super(DefaultDict,self).__init__()
			self.default_factory=default_factory
		def __getitem__(self,key):
			try:
				return super(DefaultDict,self).__getitem__(key)
			except KeyError:
				value=self.default_factory()
				self[key]=value
				return value
class WafError(Exception):
	def __init__(self,*args):
		self.args=args
		try:
			self.stack=traceback.extract_stack()
		except:
			pass
		Exception.__init__(self,*args)
	def __str__(self):
		return str(len(self.args)==1 and self.args[0]or self.args)
class WscriptError(WafError):
	def __init__(self,message,wscript_file=None):
		if wscript_file:
			self.wscript_file=wscript_file
			self.wscript_line=None
		else:
			try:
				(self.wscript_file,self.wscript_line)=self.locate_error()
			except:
				(self.wscript_file,self.wscript_line)=(None,None)
		msg_file_line=''
		if self.wscript_file:
			msg_file_line="%s:"%self.wscript_file
			if self.wscript_line:
				msg_file_line+="%s:"%self.wscript_line
		err_message="%s error: %s"%(msg_file_line,message)
		WafError.__init__(self,err_message)
	def locate_error(self):
		stack=traceback.extract_stack()
		stack.reverse()
		for frame in stack:
			file_name=os.path.basename(frame[0])
			is_wscript=(file_name==WSCRIPT_FILE or file_name==WSCRIPT_BUILD_FILE)
			if is_wscript:
				return(frame[0],frame[1])
		return(None,None)
indicator=is_win32 and'\x1b[A\x1b[K%s%s%s\r'or'\x1b[K%s%s%s\r'
try:
	from fnv import new as md5
	import Constants
	Constants.SIG_NIL='signofnv'
	def h_file(filename):
		m=md5()
		try:
			m.hfile(filename)
			x=m.digest()
			if x is None:raise OSError("not a file")
			return x
		except SystemError:
			raise OSError("not a file"+filename)
except ImportError:
	try:
		try:
			from hashlib import md5
		except ImportError:
			from md5 import md5
		def h_file(filename):
			f=open(filename,'rb')
			m=md5()
			while(filename):
				filename=f.read(100000)
				m.update(filename)
			f.close()
			return m.digest()
	except ImportError:
		md5=None
class ordered_dict(UserDict):
	def __init__(self,dict=None):
		self.allkeys=[]
		UserDict.__init__(self,dict)
	def __delitem__(self,key):
		self.allkeys.remove(key)
		UserDict.__delitem__(self,key)
	def __setitem__(self,key,item):
		if key not in self.allkeys:self.allkeys.append(key)
		UserDict.__setitem__(self,key,item)
def exec_command(s,**kw):
	if'log'in kw:
		kw['stdout']=kw['stderr']=kw['log']
		del(kw['log'])
	kw['shell']=isinstance(s,str)
	try:
		proc=pproc.Popen(s,**kw)
		return proc.wait()
	except OSError:
		return-1
if is_win32:
	def exec_command(s,**kw):
		if'log'in kw:
			kw['stdout']=kw['stderr']=kw['log']
			del(kw['log'])
		kw['shell']=isinstance(s,str)
		if len(s)>2000:
			startupinfo=pproc.STARTUPINFO()
			startupinfo.dwFlags|=pproc.STARTF_USESHOWWINDOW
			kw['startupinfo']=startupinfo
		try:
			if'stdout'not in kw:
				kw['stdout']=pproc.PIPE
				kw['stderr']=pproc.PIPE
				proc=pproc.Popen(s,**kw)
				(stdout,stderr)=proc.communicate()
				Logs.info(stdout)
				if stderr:
					Logs.error(stderr)
				return proc.returncode
			else:
				proc=pproc.Popen(s,**kw)
				return proc.wait()
		except OSError:
			return-1
listdir=os.listdir
if is_win32:
	def listdir_win32(s):
		if re.match('^[A-Za-z]:$',s):
			s+=os.sep
		if not os.path.isdir(s):
			e=OSError()
			e.errno=errno.ENOENT
			raise e
		return os.listdir(s)
	listdir=listdir_win32
def waf_version(mini=0x010000,maxi=0x100000):
	ver=HEXVERSION
	try:min_val=mini+0
	except TypeError:min_val=int(mini.replace('.','0'),16)
	if min_val>ver:
		Logs.error("waf version should be at least %s (%s found)"%(mini,ver))
		sys.exit(1)
	try:max_val=maxi+0
	except TypeError:max_val=int(maxi.replace('.','0'),16)
	if max_val<ver:
		Logs.error("waf version should be at most %s (%s found)"%(maxi,ver))
		sys.exit(1)
def python_24_guard():
	if sys.hexversion<0x20400f0 or sys.hexversion>=0x3000000:
		raise ImportError("Waf requires Python >= 2.3 but the raw source requires Python 2.4, 2.5 or 2.6")
def ex_stack():
	exc_type,exc_value,tb=sys.exc_info()
	if Logs.verbose>1:
		exc_lines=traceback.format_exception(exc_type,exc_value,tb)
		return''.join(exc_lines)
	return str(exc_value)
def to_list(sth):
	if isinstance(sth,str):
		return sth.split()
	else:
		return sth
g_loaded_modules={}
g_module=None
def load_module(file_path,name=WSCRIPT_FILE):
	try:
		return g_loaded_modules[file_path]
	except KeyError:
		pass
	module=imp.new_module(name)
	try:
		code=readf(file_path,m='rU')
	except(IOError,OSError):
		raise WscriptError('Could not read the file %r'%file_path)
	module.waf_hash_val=code
	dt=os.path.dirname(file_path)
	sys.path.insert(0,dt)
	try:
		exec(compile(code,file_path,'exec'),module.__dict__)
	except Exception:
		exc_type,exc_value,tb=sys.exc_info()
		raise WscriptError("".join(traceback.format_exception(exc_type,exc_value,tb)),file_path)
	sys.path.remove(dt)
	g_loaded_modules[file_path]=module
	return module
def set_main_module(file_path):
	global g_module
	g_module=load_module(file_path,'wscript_main')
	g_module.root_path=file_path
	try:
		g_module.APPNAME
	except:
		g_module.APPNAME='noname'
	try:
		g_module.VERSION
	except:
		g_module.VERSION='1.0'
def to_hashtable(s):
	tbl={}
	lst=s.split('\n')
	for line in lst:
		if not line:continue
		mems=line.split('=')
		tbl[mems[0]]=mems[1]
	return tbl
def get_term_cols():
	return 80
try:
	import struct,fcntl,termios
except ImportError:
	pass
else:
	if Logs.got_tty:
		def myfun():
			dummy_lines,cols=struct.unpack("HHHH",fcntl.ioctl(sys.stderr.fileno(),termios.TIOCGWINSZ,struct.pack("HHHH",0,0,0,0)))[:2]
			return cols
		try:
			myfun()
		except:
			pass
		else:
			get_term_cols=myfun
rot_idx=0
rot_chr=['\\','|','/','-']
def split_path(path):
	return path.split('/')
def split_path_cygwin(path):
	if path.startswith('//'):
		ret=path.split('/')[2:]
		ret[0]='/'+ret[0]
		return ret
	return path.split('/')
re_sp=re.compile('[/\\\\]')
def split_path_win32(path):
	if path.startswith('\\\\'):
		ret=re.split(re_sp,path)[2:]
		ret[0]='\\'+ret[0]
		return ret
	return re.split(re_sp,path)
if sys.platform=='cygwin':
	split_path=split_path_cygwin
elif is_win32:
	split_path=split_path_win32
def copy_attrs(orig,dest,names,only_if_set=False):
	for a in to_list(names):
		u=getattr(orig,a,())
		if u or not only_if_set:
			setattr(dest,a,u)
def def_attrs(cls,**kw):
	'''
	set attributes for class.
	@param cls [any class]: the class to update the given attributes in.
	@param kw [dictionary]: dictionary of attributes names and values.

	if the given class hasn't one (or more) of these attributes, add the attribute with its value to the class.
	'''
	for k,v in kw.iteritems():
		if not hasattr(cls,k):
			setattr(cls,k,v)
def quote_define_name(path):
	fu=re.compile("[^a-zA-Z0-9]").sub("_",path)
	fu=fu.upper()
	return fu
def quote_whitespace(path):
	return(path.strip().find(' ')>0 and'"%s"'%path or path).replace('""','"')
def trimquotes(s):
	if not s:return''
	s=s.rstrip()
	if s[0]=="'"and s[-1]=="'":return s[1:-1]
	return s
def h_list(lst):
	m=md5()
	m.update(str(lst))
	return m.digest()
def h_fun(fun):
	try:
		return fun.code
	except AttributeError:
		try:
			h=inspect.getsource(fun)
		except IOError:
			h="nocode"
		try:
			fun.code=h
		except AttributeError:
			pass
		return h
def pprint(col,str,label='',sep=os.linesep):
	sys.stderr.write("%s%s%s %s%s"%(Logs.colors(col),str,Logs.colors.NORMAL,label,sep))
def check_dir(dir):
	try:
		os.stat(dir)
	except OSError:
		try:
			os.makedirs(dir)
		except OSError,e:
			raise WafError("Cannot create folder '%s' (original error: %s)"%(dir,e))
def cmd_output(cmd,**kw):
	silent=False
	if'silent'in kw:
		silent=kw['silent']
		del(kw['silent'])
	if'e'in kw:
		tmp=kw['e']
		del(kw['e'])
		kw['env']=tmp
	kw['shell']=isinstance(cmd,str)
	kw['stdout']=pproc.PIPE
	if silent:
		kw['stderr']=pproc.PIPE
	try:
		p=pproc.Popen(cmd,**kw)
		output=p.communicate()[0]
	except OSError,e:
		raise ValueError(str(e))
	if p.returncode:
		if not silent:
			msg="command execution failed: %s -> %r"%(cmd,str(output))
			raise ValueError(msg)
		output=''
	return output
reg_subst=re.compile(r"(\\\\)|(\$\$)|\$\{([^}]+)\}")
def subst_vars(expr,params):
	def repl_var(m):
		if m.group(1):
			return'\\'
		if m.group(2):
			return'$'
		try:
			return params.get_flat(m.group(3))
		except AttributeError:
			return params[m.group(3)]
	return reg_subst.sub(repl_var,expr)
def unversioned_sys_platform_to_binary_format(unversioned_sys_platform):
	if unversioned_sys_platform in('linux','freebsd','netbsd','openbsd','sunos','gnu'):
		return'elf'
	elif unversioned_sys_platform=='darwin':
		return'mac-o'
	elif unversioned_sys_platform in('win32','cygwin','uwin','msys'):
		return'pe'
	return'elf'
def unversioned_sys_platform():
	s=sys.platform
	if s=='java':
		from java.lang import System
		s=System.getProperty('os.name')
		if s=='Mac OS X':
			return'darwin'
		elif s.startswith('Windows '):
			return'win32'
		elif s=='OS/2':
			return'os2'
		elif s=='HP-UX':
			return'hpux'
		elif s in('SunOS','Solaris'):
			return'sunos'
		else:s=s.lower()
	if s=='win32'or s.endswith('os2')and s!='sunos2':return s
	return re.split('\d+$',s)[0]
def detect_platform():
	s=sys.platform
	for x in'cygwin linux irix sunos hpux aix darwin gnu'.split():
		if s.find(x)>=0:
			return x
	if os.name in'posix java os2'.split():
		return os.name
	return s
def load_tool(tool,tooldir=None):
	'''
	load_tool: import a Python module, optionally using several directories.
	@param tool [string]: name of tool to import.
	@param tooldir [list]: directories to look for the tool.
	@return: the loaded module.

	Warning: this function is not thread-safe: plays with sys.path,
					 so must run in sequence.
	'''
	if tooldir:
		assert isinstance(tooldir,list)
		sys.path=tooldir+sys.path
	else:
		tooldir=[]
	try:
		return __import__(tool)
	finally:
		for dt in tooldir:
			sys.path.remove(dt)
def readf(fname,m='r'):
	f=open(fname,m)
	try:
		txt=f.read()
	finally:
		f.close()
	return txt
def nada(*k,**kw):
	pass
def diff_path(top,subdir):
	top=os.path.normpath(top).replace('\\','/').split('/')
	subdir=os.path.normpath(subdir).replace('\\','/').split('/')
	if len(top)==len(subdir):return''
	diff=subdir[len(top)-len(subdir):]
	return os.path.join(*diff)
class Context(object):
	def set_curdir(self,dir):
		self.curdir_=dir
	def get_curdir(self):
		try:
			return self.curdir_
		except AttributeError:
			self.curdir_=os.getcwd()
			return self.get_curdir()
	curdir=property(get_curdir,set_curdir)
	def recurse(self,dirs,name=''):
		if not name:
			name=inspect.stack()[1][3]
		if isinstance(dirs,str):
			dirs=to_list(dirs)
		for x in dirs:
			if os.path.isabs(x):
				nexdir=x
			else:
				nexdir=os.path.join(self.curdir,x)
			base=os.path.join(nexdir,WSCRIPT_FILE)
			file_path=base+'_'+name
			try:
				txt=readf(file_path,m='rU')
			except(OSError,IOError):
				try:
					module=load_module(base)
				except OSError:
					raise WscriptError('No such script %s'%base)
				try:
					f=module.__dict__[name]
				except KeyError:
					raise WscriptError('No function %s defined in %s'%(name,base))
				if getattr(self.__class__,'pre_recurse',None):
					self.pre_recurse(f,base,nexdir)
				old=self.curdir
				self.curdir=nexdir
				try:
					f(self)
				finally:
					self.curdir=old
				if getattr(self.__class__,'post_recurse',None):
					self.post_recurse(module,base,nexdir)
			else:
				dc={'ctx':self}
				if getattr(self.__class__,'pre_recurse',None):
					dc=self.pre_recurse(txt,file_path,nexdir)
				old=self.curdir
				self.curdir=nexdir
				try:
					try:
						exec(compile(txt,file_path,'exec'),dc)
					except Exception:
						exc_type,exc_value,tb=sys.exc_info()
						raise WscriptError("".join(traceback.format_exception(exc_type,exc_value,tb)),base)
				finally:
					self.curdir=old
				if getattr(self.__class__,'post_recurse',None):
					self.post_recurse(txt,file_path,nexdir)
if is_win32:
	old=shutil.copy2
	def copy2(src,dst):
		old(src,dst)
		shutil.copystat(src,src)
	setattr(shutil,'copy2',copy2)
def zip_folder(dir,zip_file_name,prefix):
	import zipfile
	zip=zipfile.ZipFile(zip_file_name,'w',compression=zipfile.ZIP_DEFLATED)
	base=os.path.abspath(dir)
	if prefix:
		if prefix[-1]!=os.sep:
			prefix+=os.sep
	n=len(base)
	for root,dirs,files in os.walk(base):
		for f in files:
			archive_name=prefix+root[n:]+os.sep+f
			zip.write(root+os.sep+f,archive_name,zipfile.ZIP_DEFLATED)
	zip.close()
def get_elapsed_time(start):
	delta=datetime.datetime.now()-start
	days=int(delta.days)
	hours=int(delta.seconds/3600)
	minutes=int((delta.seconds-hours*3600)/60)
	seconds=delta.seconds-hours*3600-minutes*60+float(delta.microseconds)/1000/1000
	result=''
	if days:
		result+='%dd'%days
	if days or hours:
		result+='%dh'%hours
	if days or hours or minutes:
		result+='%dm'%minutes
	return'%s%.3fs'%(result,seconds)
if os.name=='java':
	try:
		gc.disable()
		gc.enable()
	except NotImplementedError:
		gc.disable=gc.enable

