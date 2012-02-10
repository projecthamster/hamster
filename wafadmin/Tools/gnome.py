#! /usr/bin/env python
# encoding: utf-8

import os,re
import TaskGen,Utils,Runner,Task,Build,Options,Logs
from Logs import error
from TaskGen import taskgen,before,after,feature
n1_regexp=re.compile('<refentrytitle>(.*)</refentrytitle>',re.M)
n2_regexp=re.compile('<manvolnum>(.*)</manvolnum>',re.M)
def postinstall_schemas(prog_name):
	if Build.bld.is_install:
		dir=Build.bld.get_install_path('${SYSCONFDIR}/gconf/schemas/%s.schemas'%prog_name)
		if not Options.options.destdir:
			Utils.pprint('YELLOW','Installing GConf schema')
			command='gconftool-2 --install-schema-file=%s 1> /dev/null'%dir
			ret=Utils.exec_command(command)
		else:
			Utils.pprint('YELLOW','GConf schema not installed. After install, run this:')
			Utils.pprint('YELLOW','gconftool-2 --install-schema-file=%s'%dir)
def postinstall_icons():
	dir=Build.bld.get_install_path('${DATADIR}/icons/hicolor')
	if Build.bld.is_install:
		if not Options.options.destdir:
			Utils.pprint('YELLOW',"Updating Gtk icon cache.")
			command='gtk-update-icon-cache -q -f -t %s'%dir
			ret=Utils.exec_command(command)
		else:
			Utils.pprint('YELLOW','Icon cache not updated. After install, run this:')
			Utils.pprint('YELLOW','gtk-update-icon-cache -q -f -t %s'%dir)
def postinstall_scrollkeeper(prog_name):
	if Build.bld.is_install:
		if os.access('/var/log/scrollkeeper.log',os.W_OK):
			dir1=Build.bld.get_install_path('${PREFIX}/var/scrollkeeper')
			dir2=Build.bld.get_install_path('${DATADIR}/omf/%s'%prog_name)
			command='scrollkeeper-update -q -p %s -o %s'%(dir1,dir2)
			ret=Utils.exec_command(command)
def postinstall(prog_name='myapp',schemas=1,icons=1,scrollkeeper=1):
	if schemas:postinstall_schemas(prog_name)
	if icons:postinstall_icons()
	if scrollkeeper:postinstall_scrollkeeper(prog_name)
class gnome_doc_taskgen(TaskGen.task_gen):
	def __init__(self,*k,**kw):
		TaskGen.task_gen.__init__(self,*k,**kw)
def init_gnome_doc(self):
	self.default_install_path='${PREFIX}/share'
def apply_gnome_doc(self):
	self.env['APPNAME']=self.doc_module
	lst=self.to_list(self.doc_linguas)
	bld=self.bld
	lst.append('C')
	for x in lst:
		if not x=='C':
			tsk=self.create_task('xml2po')
			node=self.path.find_resource(x+'/'+x+'.po')
			src=self.path.find_resource('C/%s.xml'%self.doc_module)
			out=self.path.find_or_declare('%s/%s.xml'%(x,self.doc_module))
			tsk.set_inputs([node,src])
			tsk.set_outputs(out)
		else:
			out=self.path.find_resource('%s/%s.xml'%(x,self.doc_module))
		tsk2=self.create_task('xsltproc2po')
		out2=self.path.find_or_declare('%s/%s-%s.omf'%(x,self.doc_module,x))
		tsk2.set_outputs(out2)
		node=self.path.find_resource(self.doc_module+".omf.in")
		tsk2.inputs=[node,out]
		tsk2.run_after.append(tsk)
		if bld.is_install:
			path=self.install_path+'/gnome/help/%s/%s'%(self.doc_module,x)
			bld.install_files(self.install_path+'/omf',out2,env=self.env)
			for y in self.to_list(self.doc_figures):
				try:
					os.stat(self.path.abspath()+'/'+x+'/'+y)
					bld.install_as(path+'/'+y,self.path.abspath()+'/'+x+'/'+y)
				except:
					bld.install_as(path+'/'+y,self.path.abspath()+'/C/'+y)
			bld.install_as(path+'/%s.xml'%self.doc_module,out.abspath(self.env))
			if x=='C':
				xmls=self.to_list(self.doc_includes)
				xmls.append(self.doc_entities)
				for z in xmls:
					out=self.path.find_resource('%s/%s'%(x,z))
					bld.install_as(path+'/%s'%z,out.abspath(self.env))
class xml_to_taskgen(TaskGen.task_gen):
	def __init__(self,*k,**kw):
		TaskGen.task_gen.__init__(self,*k,**kw)
def init_xml_to(self):
	Utils.def_attrs(self,source='xmlfile',xslt='xlsltfile',target='hey',default_install_path='${PREFIX}',task_created=None)
def apply_xml_to(self):
	xmlfile=self.path.find_resource(self.source)
	xsltfile=self.path.find_resource(self.xslt)
	tsk=self.create_task('xmlto',[xmlfile,xsltfile],xmlfile.change_ext('html'))
	tsk.install_path=self.install_path
def sgml_scan(self):
	node=self.inputs[0]
	env=self.env
	variant=node.variant(env)
	fi=open(node.abspath(env),'r')
	content=fi.read()
	fi.close()
	name=n1_regexp.findall(content)[0]
	num=n2_regexp.findall(content)[0]
	doc_name=name+'.'+num
	if not self.outputs:
		self.outputs=[self.generator.path.find_or_declare(doc_name)]
	return([],[doc_name])
class gnome_sgml2man_taskgen(TaskGen.task_gen):
	def __init__(self,*k,**kw):
		TaskGen.task_gen.__init__(self,*k,**kw)
def apply_gnome_sgml2man(self):
	assert(getattr(self,'appname',None))
	def install_result(task):
		out=task.outputs[0]
		name=out.name
		ext=name[-1]
		env=task.env
		self.bld.install_files('${DATADIR}/man/man%s/'%ext,out,env)
	self.bld.rescan(self.path)
	for name in self.bld.cache_dir_contents[self.path.id]:
		base,ext=os.path.splitext(name)
		if ext!='.sgml':continue
		task=self.create_task('sgml2man')
		task.set_inputs(self.path.find_resource(name))
		task.task_generator=self
		if self.bld.is_install:task.install=install_result
		task.scan()
cls=Task.simple_task_type('sgml2man','${SGML2MAN} -o ${TGT[0].bld_dir(env)} ${SRC}  > /dev/null',color='BLUE')
cls.scan=sgml_scan
cls.quiet=1
Task.simple_task_type('xmlto','${XMLTO} html -m ${SRC[1].abspath(env)} ${SRC[0].abspath(env)}')
Task.simple_task_type('xml2po','${XML2PO} ${XML2POFLAGS} ${SRC} > ${TGT}',color='BLUE')
xslt_magic="""${XSLTPROC2PO} -o ${TGT[0].abspath(env)} \
--stringparam db2omf.basename ${APPNAME} \
--stringparam db2omf.format docbook \
--stringparam db2omf.lang ${TGT[0].abspath(env)[:-4].split('-')[-1]} \
--stringparam db2omf.dtd '-//OASIS//DTD DocBook XML V4.3//EN' \
--stringparam db2omf.omf_dir ${PREFIX}/share/omf \
--stringparam db2omf.help_dir ${PREFIX}/share/gnome/help \
--stringparam db2omf.omf_in ${SRC[0].abspath(env)} \
--stringparam db2omf.scrollkeeper_cl ${SCROLLKEEPER_DATADIR}/Templates/C/scrollkeeper_cl.xml \
${DB2OMF} ${SRC[1].abspath(env)}"""
Task.simple_task_type('xsltproc2po',xslt_magic,color='BLUE')
def detect(conf):
	conf.check_tool('gnu_dirs glib2 dbus')
	sgml2man=conf.find_program('docbook2man',var='SGML2MAN')
	def getstr(varname):
		return getattr(Options.options,varname,'')
	conf.define('GNOMELOCALEDIR',os.path.join(conf.env['DATADIR'],'locale'))
	xml2po=conf.find_program('xml2po',var='XML2PO')
	xsltproc2po=conf.find_program('xsltproc',var='XSLTPROC2PO')
	conf.env['XML2POFLAGS']='-e -p'
	conf.env['SCROLLKEEPER_DATADIR']=Utils.cmd_output("scrollkeeper-config --pkgdatadir",silent=1).strip()
	conf.env['DB2OMF']=Utils.cmd_output("/usr/bin/pkg-config --variable db2omf gnome-doc-utils",silent=1).strip()
def set_options(opt):
	opt.add_option('--want-rpath',type='int',default=1,dest='want_rpath',help='set rpath to 1 or 0 [Default 1]')

feature('gnome_doc')(init_gnome_doc)
feature('gnome_doc')(apply_gnome_doc)
after('init_gnome_doc')(apply_gnome_doc)
feature('xml_to')(init_xml_to)
feature('xml_to')(apply_xml_to)
after('init_xml_to')(apply_xml_to)
feature('gnome_sgml2man')(apply_gnome_sgml2man)
