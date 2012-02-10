#! /usr/bin/env python
# encoding: utf-8
import sys
if sys.hexversion < 0x020400f0: from sets import Set as set
import os,copy,re
import Logs,Options,Utils
from Constants import*
re_imp=re.compile('^(#)*?([^#=]*?)\ =\ (.*?)$',re.M)
class Environment(object):
	__slots__=("table","parent")
	def __init__(self,filename=None):
		self.table={}
		if filename:
			self.load(filename)
	def __contains__(self,key):
		if key in self.table:return True
		try:return self.parent.__contains__(key)
		except AttributeError:return False
	def __str__(self):
		keys=set()
		cur=self
		while cur:
			keys.update(cur.table.keys())
			cur=getattr(cur,'parent',None)
		keys=list(keys)
		keys.sort()
		return"\n".join(["%r %r"%(x,self.__getitem__(x))for x in keys])
	def __getitem__(self,key):
		try:
			while 1:
				x=self.table.get(key,None)
				if not x is None:
					return x
				self=self.parent
		except AttributeError:
			return[]
	def __setitem__(self,key,value):
		self.table[key]=value
	def __delitem__(self,key):
		del self.table[key]
	def pop(self,key,*args):
		if len(args):
			return self.table.pop(key,*args)
		return self.table.pop(key)
	def set_variant(self,name):
		self.table[VARIANT]=name
	def variant(self):
		try:
			while 1:
				x=self.table.get(VARIANT,None)
				if not x is None:
					return x
				self=self.parent
		except AttributeError:
			return DEFAULT
	def copy(self):
		newenv=Environment()
		newenv.parent=self
		return newenv
	def detach(self):
		tbl=self.get_merged_dict()
		try:
			delattr(self,'parent')
		except AttributeError:
			pass
		else:
			keys=tbl.keys()
			for x in keys:
				tbl[x]=copy.deepcopy(tbl[x])
			self.table=tbl
	def get_flat(self,key):
		s=self[key]
		if isinstance(s,str):return s
		return' '.join(s)
	def _get_list_value_for_modification(self,key):
		try:
			value=self.table[key]
		except KeyError:
			try:value=self.parent[key]
			except AttributeError:value=[]
			if isinstance(value,list):
				value=value[:]
			else:
				value=[value]
		else:
			if not isinstance(value,list):
				value=[value]
		self.table[key]=value
		return value
	def append_value(self,var,value):
		current_value=self._get_list_value_for_modification(var)
		if isinstance(value,list):
			current_value.extend(value)
		else:
			current_value.append(value)
	def prepend_value(self,var,value):
		current_value=self._get_list_value_for_modification(var)
		if isinstance(value,list):
			current_value=value+current_value
			self.table[var]=current_value
		else:
			current_value.insert(0,value)
	def append_unique(self,var,value):
		current_value=self._get_list_value_for_modification(var)
		if isinstance(value,list):
			for value_item in value:
				if value_item not in current_value:
					current_value.append(value_item)
		else:
			if value not in current_value:
				current_value.append(value)
	def get_merged_dict(self):
		table_list=[]
		env=self
		while 1:
			table_list.insert(0,env.table)
			try:env=env.parent
			except AttributeError:break
		merged_table={}
		for table in table_list:
			merged_table.update(table)
		return merged_table
	def store(self,filename):
		file=open(filename,'w')
		merged_table=self.get_merged_dict()
		keys=list(merged_table.keys())
		keys.sort()
		for k in keys:file.write('%s = %r\n'%(k,merged_table[k]))
		file.close()
	def load(self,filename):
		tbl=self.table
		code=Utils.readf(filename)
		for m in re_imp.finditer(code):
			g=m.group
			tbl[g(2)]=eval(g(3))
		Logs.debug('env: %s',self.table)
	def get_destdir(self):
		if self.__getitem__('NOINSTALL'):return''
		return Options.options.destdir
	def update(self,d):
		for k,v in d.iteritems():
			self[k]=v
	def __getattr__(self,name):
		if name in self.__slots__:
			return object.__getattr__(self,name)
		else:
			return self[name]
	def __setattr__(self,name,value):
		if name in self.__slots__:
			object.__setattr__(self,name,value)
		else:
			self[name]=value
	def __delattr__(self,name):
		if name in self.__slots__:
			object.__delattr__(self,name)
		else:
			del self[name]

