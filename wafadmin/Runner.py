#! /usr/bin/env python
# encoding: utf-8
import sys
if sys.hexversion < 0x020400f0: from sets import Set as set
import os,sys,random,time,threading,traceback
try:from Queue import Queue
except ImportError:from queue import Queue
import Build,Utils,Logs,Options
from Logs import debug,error
from Constants import*
GAP=15
run_old=threading.Thread.run
def run(*args,**kwargs):
	try:
		run_old(*args,**kwargs)
	except(KeyboardInterrupt,SystemExit):
		raise
	except:
		sys.excepthook(*sys.exc_info())
threading.Thread.run=run
class TaskConsumer(threading.Thread):
	ready=Queue(0)
	consumers=[]
	def __init__(self):
		threading.Thread.__init__(self)
		self.setDaemon(1)
		self.start()
	def run(self):
		try:
			self.loop()
		except:
			pass
	def loop(self):
		while 1:
			tsk=TaskConsumer.ready.get()
			m=tsk.master
			if m.stop:
				m.out.put(tsk)
				continue
			try:
				tsk.generator.bld.printout(tsk.display())
				if tsk.__class__.stat:ret=tsk.__class__.stat(tsk)
				else:ret=tsk.call_run()
			except Exception,e:
				tsk.err_msg=Utils.ex_stack()
				tsk.hasrun=EXCEPTION
				m.error_handler(tsk)
				m.out.put(tsk)
				continue
			if ret:
				tsk.err_code=ret
				tsk.hasrun=CRASHED
			else:
				try:
					tsk.post_run()
				except Utils.WafError:
					pass
				except Exception:
					tsk.err_msg=Utils.ex_stack()
					tsk.hasrun=EXCEPTION
				else:
					tsk.hasrun=SUCCESS
			if tsk.hasrun!=SUCCESS:
				m.error_handler(tsk)
			m.out.put(tsk)
class Parallel(object):
	def __init__(self,bld,j=2):
		self.numjobs=j
		self.manager=bld.task_manager
		self.manager.current_group=0
		self.total=self.manager.total()
		self.outstanding=[]
		self.maxjobs=MAXJOBS
		self.frozen=[]
		self.out=Queue(0)
		self.count=0
		self.processed=1
		self.stop=False
		self.error=False
	def get_next(self):
		if not self.outstanding:
			return None
		return self.outstanding.pop(0)
	def postpone(self,tsk):
		if random.randint(0,1):
			self.frozen.insert(0,tsk)
		else:
			self.frozen.append(tsk)
	def refill_task_list(self):
		while self.count>self.numjobs+GAP or self.count>=self.maxjobs:
			self.get_out()
		while not self.outstanding:
			if self.count:
				self.get_out()
			if self.frozen:
				self.outstanding+=self.frozen
				self.frozen=[]
			elif not self.count:
				(jobs,tmp)=self.manager.get_next_set()
				if jobs!=None:self.maxjobs=jobs
				if tmp:self.outstanding+=tmp
				break
	def get_out(self):
		ret=self.out.get()
		self.manager.add_finished(ret)
		if not self.stop and getattr(ret,'more_tasks',None):
			self.outstanding+=ret.more_tasks
			self.total+=len(ret.more_tasks)
		self.count-=1
	def error_handler(self,tsk):
		if not Options.options.keep:
			self.stop=True
		self.error=True
	def start(self):
		if TaskConsumer.consumers:
			while len(TaskConsumer.consumers)<self.numjobs:
				TaskConsumer.consumers.append(TaskConsumer())
		while not self.stop:
			self.refill_task_list()
			tsk=self.get_next()
			if not tsk:
				if self.count:
					continue
				else:
					break
			if tsk.hasrun:
				self.processed+=1
				self.manager.add_finished(tsk)
				continue
			try:
				st=tsk.runnable_status()
			except Exception,e:
				self.processed+=1
				if self.stop and not Options.options.keep:
					tsk.hasrun=SKIPPED
					self.manager.add_finished(tsk)
					continue
				self.error_handler(tsk)
				self.manager.add_finished(tsk)
				tsk.hasrun=EXCEPTION
				tsk.err_msg=Utils.ex_stack()
				continue
			if st==ASK_LATER:
				self.postpone(tsk)
			elif st==SKIP_ME:
				self.processed+=1
				tsk.hasrun=SKIPPED
				self.manager.add_finished(tsk)
			else:
				tsk.position=(self.processed,self.total)
				self.count+=1
				tsk.master=self
				TaskConsumer.ready.put(tsk)
				self.processed+=1
				if not TaskConsumer.consumers:
					TaskConsumer.consumers=[TaskConsumer()for i in xrange(self.numjobs)]
		while self.error and self.count:
			self.get_out()
		assert(self.count==0 or self.stop)

