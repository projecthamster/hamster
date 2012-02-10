#! /usr/bin/env python
# encoding: utf-8
import sys
if sys.hexversion < 0x020400f0: from sets import Set as set
import os,traceback,copy
import Build,Task,Utils,Logs,Options
from Logs import debug,error,warn
from Constants import*
typos={'sources':'source','targets':'target','include':'includes','define':'defines','importpath':'importpaths','install_var':'install_path','install_subdir':'install_path','inst_var':'install_path','inst_dir':'install_path','feature':'features',}
class register_obj(type):
	def __init__(cls,name,bases,dict):
		super(register_obj,cls).__init__(name,bases,dict)
		name=cls.__name__
		suffix='_taskgen'
		if name.endswith(suffix):
			task_gen.classes[name.replace(suffix,'')]=cls
class task_gen(object):
	__metaclass__=register_obj
	mappings={}
	mapped={}
	prec=Utils.DefaultDict(list)
	traits=Utils.DefaultDict(set)
	classes={}
	def __init__(self,*kw,**kwargs):
		self.prec=Utils.DefaultDict(list)
		self.source=''
		self.target=''
		self.meths=[]
		self.mappings={}
		self.features=list(kw)
		self.tasks=[]
		self.default_chmod=O644
		self.default_install_path=None
		self.allnodes=[]
		self.bld=kwargs.get('bld',Build.bld)
		self.env=self.bld.env.copy()
		self.path=self.bld.path
		self.name=''
		self.idx=self.bld.idx[self.path.id]=self.bld.idx.get(self.path.id,0)+1
		for key,val in kwargs.iteritems():
			setattr(self,key,val)
		self.bld.task_manager.add_task_gen(self)
		self.bld.all_task_gen.append(self)
	def __str__(self):
		return("<task_gen '%s' of type %s defined in %s>"%(self.name or self.target,self.__class__.__name__,str(self.path)))
	def __setattr__(self,name,attr):
		real=typos.get(name,name)
		if real!=name:
			warn('typo %s -> %s'%(name,real))
			if Logs.verbose>0:
				traceback.print_stack()
		object.__setattr__(self,real,attr)
	def to_list(self,value):
		if isinstance(value,str):return value.split()
		else:return value
	def apply(self):
		keys=set(self.meths)
		self.features=Utils.to_list(self.features)
		for x in self.features+['*']:
			st=task_gen.traits[x]
			if not st:
				warn('feature %r does not exist - bind at least one method to it'%x)
			keys.update(st)
		prec={}
		prec_tbl=self.prec or task_gen.prec
		for x in prec_tbl:
			if x in keys:
				prec[x]=prec_tbl[x]
		tmp=[]
		for a in keys:
			for x in prec.values():
				if a in x:break
			else:
				tmp.append(a)
		out=[]
		while tmp:
			e=tmp.pop()
			if e in keys:out.append(e)
			try:
				nlst=prec[e]
			except KeyError:
				pass
			else:
				del prec[e]
				for x in nlst:
					for y in prec:
						if x in prec[y]:
							break
					else:
						tmp.append(x)
		if prec:raise Utils.WafError("graph has a cycle %s"%str(prec))
		out.reverse()
		self.meths=out
		debug('task_gen: posting %s %d',self,id(self))
		for x in out:
			try:
				v=getattr(self,x)
			except AttributeError:
				raise Utils.WafError("tried to retrieve %s which is not a valid method"%x)
			debug('task_gen: -> %s (%d)',x,id(self))
			v()
	def post(self):
		if not self.name:
			if isinstance(self.target,list):
				self.name=' '.join(self.target)
			else:
				self.name=self.target
		if getattr(self,'posted',None):
			return
		self.apply()
		self.posted=True
		debug('task_gen: posted %s',self.name)
	def get_hook(self,ext):
		try:return self.mappings[ext]
		except KeyError:
			try:return task_gen.mappings[ext]
			except KeyError:return None
	def create_task(self,name,src=None,tgt=None,env=None):
		env=env or self.env
		task=Task.TaskBase.classes[name](env.copy(),generator=self)
		if src:
			task.set_inputs(src)
		if tgt:
			task.set_outputs(tgt)
		self.tasks.append(task)
		return task
	def name_to_obj(self,name):
		return self.bld.name_to_obj(name,self.env)
	def find_sources_in_dirs(self,dirnames,excludes=[],exts=[]):
		err_msg="'%s' attribute must be a list"
		if not isinstance(excludes,list):
			raise Utils.WscriptError(err_msg%'excludes')
		if not isinstance(exts,list):
			raise Utils.WscriptError(err_msg%'exts')
		lst=[]
		dirnames=self.to_list(dirnames)
		ext_lst=exts or list(self.mappings.keys())+list(task_gen.mappings.keys())
		for name in dirnames:
			anode=self.path.find_dir(name)
			if not anode or not anode.is_child_of(self.bld.srcnode):
				raise Utils.WscriptError("Unable to use '%s' - either because it's not a relative path"", or it's not child of '%s'."%(name,self.bld.srcnode))
			self.bld.rescan(anode)
			for name in self.bld.cache_dir_contents[anode.id]:
				if name.startswith('.'):
					continue
				(base,ext)=os.path.splitext(name)
				if ext in ext_lst and not name in lst and not name in excludes:
					lst.append((anode.relpath_gen(self.path)or'.')+os.path.sep+name)
		lst.sort()
		self.source=self.to_list(self.source)
		if not self.source:self.source=lst
		else:self.source+=lst
	def clone(self,env):
		newobj=task_gen(bld=self.bld)
		for x in self.__dict__:
			if x in['env','bld']:
				continue
			elif x in["path","features"]:
				setattr(newobj,x,getattr(self,x))
			else:
				setattr(newobj,x,copy.copy(getattr(self,x)))
		newobj.__class__=self.__class__
		if isinstance(env,str):
			newobj.env=self.bld.all_envs[env].copy()
		else:
			newobj.env=env.copy()
		return newobj
	def get_inst_path(self):
		return getattr(self,'_install_path',getattr(self,'default_install_path',''))
	def set_inst_path(self,val):
		self._install_path=val
	install_path=property(get_inst_path,set_inst_path)
	def get_chmod(self):
		return getattr(self,'_chmod',getattr(self,'default_chmod',O644))
	def set_chmod(self,val):
		self._chmod=val
	chmod=property(get_chmod,set_chmod)
def declare_extension(var,func):
	try:
		for x in Utils.to_list(var):
			task_gen.mappings[x]=func
	except:
		raise Utils.WscriptError('declare_extension takes either a list or a string %r'%var)
	task_gen.mapped[func.__name__]=func
def declare_order(*k):
	assert(len(k)>1)
	n=len(k)-1
	for i in xrange(n):
		f1=k[i]
		f2=k[i+1]
		if not f1 in task_gen.prec[f2]:
			task_gen.prec[f2].append(f1)
def declare_chain(name='',action='',ext_in='',ext_out='',reentrant=True,color='BLUE',install=0,before=[],after=[],decider=None,rule=None,scan=None):
	action=action or rule
	if isinstance(action,str):
		act=Task.simple_task_type(name,action,color=color)
	else:
		act=Task.task_type_from_func(name,action,color=color)
	act.ext_in=tuple(Utils.to_list(ext_in))
	act.ext_out=tuple(Utils.to_list(ext_out))
	act.before=Utils.to_list(before)
	act.after=Utils.to_list(after)
	act.scan=scan
	def x_file(self,node):
		if decider:
			ext=decider(self,node)
		else:
			ext=ext_out
		if isinstance(ext,str):
			out_source=node.change_ext(ext)
			if reentrant:
				self.allnodes.append(out_source)
		elif isinstance(ext,list):
			out_source=[node.change_ext(x)for x in ext]
			if reentrant:
				for i in xrange((reentrant is True)and len(out_source)or reentrant):
					self.allnodes.append(out_source[i])
		else:
			raise Utils.WafError("do not know how to process %s"%str(ext))
		tsk=self.create_task(name,node,out_source)
		if node.__class__.bld.is_install:
			tsk.install=install
	declare_extension(act.ext_in,x_file)
	return x_file
def bind_feature(name,methods):
	lst=Utils.to_list(methods)
	task_gen.traits[name].update(lst)
def taskgen(func):
	setattr(task_gen,func.__name__,func)
	return func
def feature(*k):
	def deco(func):
		setattr(task_gen,func.__name__,func)
		for name in k:
			task_gen.traits[name].update([func.__name__])
		return func
	return deco
def before(*k):
	def deco(func):
		setattr(task_gen,func.__name__,func)
		for fun_name in k:
			if not func.__name__ in task_gen.prec[fun_name]:
				task_gen.prec[fun_name].append(func.__name__)
		return func
	return deco
def after(*k):
	def deco(func):
		setattr(task_gen,func.__name__,func)
		for fun_name in k:
			if not fun_name in task_gen.prec[func.__name__]:
				task_gen.prec[func.__name__].append(fun_name)
		return func
	return deco
def extension(var):
	def deco(func):
		setattr(task_gen,func.__name__,func)
		try:
			for x in Utils.to_list(var):
				task_gen.mappings[x]=func
		except:
			raise Utils.WafError('extension takes either a list or a string %r'%var)
		task_gen.mapped[func.__name__]=func
		return func
	return deco
def apply_core(self):
	find_resource=self.path.find_resource
	for filename in self.to_list(self.source):
		x=self.get_hook(filename)
		if x:
			x(self,filename)
		else:
			node=find_resource(filename)
			if not node:raise Utils.WafError("source not found: '%s' in '%s'"%(filename,str(self.path)))
			self.allnodes.append(node)
	for node in self.allnodes:
		x=self.get_hook(node.suffix())
		if not x:
			raise Utils.WafError("Cannot guess how to process %s (got mappings %r in %r) -> try conf.check_tool(..)?"%(str(node),self.__class__.mappings.keys(),self.__class__))
		x(self,node)
feature('*')(apply_core)
def exec_rule(self):
	if not getattr(self,'rule',None):
		return
	try:
		self.meths.remove('apply_core')
	except ValueError:
		pass
	func=self.rule
	vars2=[]
	if isinstance(func,str):
		(func,vars2)=Task.compile_fun('',self.rule,shell=getattr(self,'shell',True))
		func.code=self.rule
	name=getattr(self,'name',None)or self.target or self.rule
	if not isinstance(name,str):
		name=str(self.idx)
	cls=Task.task_type_from_func(name,func,getattr(self,'vars',vars2))
	tsk=self.create_task(name)
	dep_vars=getattr(self,'dep_vars',['ruledeps'])
	if dep_vars:
		tsk.dep_vars=dep_vars
	if isinstance(self.rule,str):
		tsk.env.ruledeps=self.rule
	else:
		tsk.env.ruledeps=Utils.h_fun(self.rule)
	if getattr(self,'target',None):
		cls.quiet=True
		tsk.outputs=[self.path.find_or_declare(x)for x in self.to_list(self.target)]
	if getattr(self,'source',None):
		cls.quiet=True
		tsk.inputs=[]
		for x in self.to_list(self.source):
			y=self.path.find_resource(x)
			if not y:
				raise Utils.WafError('input file %r could not be found (%r)'%(x,self.path.abspath()))
			tsk.inputs.append(y)
	if self.allnodes:
		tsk.inputs.extend(self.allnodes)
	if getattr(self,'scan',None):
		cls.scan=self.scan
	if getattr(self,'install_path',None):
		tsk.install_path=self.install_path
	if getattr(self,'cwd',None):
		tsk.cwd=self.cwd
	if getattr(self,'on_results',None):
		Task.update_outputs(cls)
	if getattr(self,'always',None):
		Task.always_run(cls)
	for x in['after','before','ext_in','ext_out']:
		setattr(cls,x,getattr(self,x,[]))
feature('*')(exec_rule)
before('apply_core')(exec_rule)
def sequence_order(self):
	if self.meths and self.meths[-1]!='sequence_order':
		self.meths.append('sequence_order')
		return
	if getattr(self,'seq_start',None):
		return
	if getattr(self.bld,'prev',None):
		self.bld.prev.post()
		for x in self.bld.prev.tasks:
			for y in self.tasks:
				y.set_run_after(x)
	self.bld.prev=self
feature('seq')(sequence_order)

