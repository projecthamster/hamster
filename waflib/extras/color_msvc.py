#!/usr/bin/env python
# encoding: utf-8

# Replaces the default formatter by one which understands MSVC output and colorizes it.
# Modified from color_gcc.py

__author__ = __maintainer__ = "Alibek Omarov <a1ba.omarov@gmail.com>"
__copyright__ = "Alibek Omarov, 2019"

import sys
from waflib import Logs

class ColorMSVCFormatter(Logs.formatter):
	def __init__(self, colors):
		self.colors = colors
		Logs.formatter.__init__(self)
	
	def parseMessage(self, line, color):
		# Split messaage from 'disk:filepath: type: message'
		arr = line.split(':', 3)
		if len(arr) < 4:
			return line
		
		colored = self.colors.BOLD + arr[0] + ':' + arr[1] + ':' + self.colors.NORMAL
		colored += color + arr[2] + ':' + self.colors.NORMAL
		colored += arr[3]
		return colored
	
	def format(self, rec):
		frame = sys._getframe()
		while frame:
			func = frame.f_code.co_name
			if func == 'exec_command':
				cmd = frame.f_locals.get('cmd')
				if isinstance(cmd, list):
					# Fix file case, it may be CL.EXE or cl.exe
					argv0 = cmd[0].lower()
					if 'cl.exe' in argv0:
						
						# This will not work with "localized" versions
						# of MSVC
                        lines = [self.parseMessage(line, self.colors.YELLOW) 
                                 if ': warning ' in line else 
                                                            self.parseMessage(line, self.colors.RED) if ': error ' in line else 
                                                                self.parseMessage(line, self.colors.RED + self.colors.BOLD) if ': fatal error ' in line else 
                                                                    self.parseMessage(line, self.colors.CYAN) if ': note: ' in line else 
                                                                            line for line in rec.msg.splitlines()]
						rec.msg = "\n".join(lines)
			frame = frame.f_back
		return Logs.formatter.format(self, rec)

def options(opt):
	Logs.log.handlers[0].setFormatter(ColorMSVCFormatter(Logs.colors))

