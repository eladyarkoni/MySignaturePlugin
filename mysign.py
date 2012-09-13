#-----------------------------------------------------------------------------------
# MySignature Sublime Text Plugin
# Author: Elad Yarkoni
# Version: 1.0
# Description: Sublime text autocomplete improvements: 
#				- showing javascript methods with parameters
#-----------------------------------------------------------------------------------
import sublime, sublime_plugin, os, re, threading

#
# Method Class
#
class Method:
	_name = ""
	_signature = ""
	def __init__(self, name, signature):
		self._name = name
		self._signature = signature
	def name(self):
		return self._name
	def signature(self):
		return self._signature

#
# MySign Class
#
class MySign:
	_functions = []
	MAX_WORD_SIZE = 100
	MAX_FUNC_SIZE = 50
	def clear(self):
		self._functions = []
	def addFunc(self, name, signature):
		self._functions.append(Method(name, signature))
	def get_autocomplete_list(self, word):
		autocomplete_list = []
		for method_obj in self._functions:
			if word in method_obj.name():
				autocomplete_list.append((method_obj.name() + '(' + method_obj.signature()+ ')','')) 
		return autocomplete_list

#
# MySign Collector Thread
#
class MySignCollectorThread(threading.Thread):
	
	def __init__(self, collector, open_folder_arr, timeout_seconds):  
		self.collector = collector
		self.timeout = timeout_seconds
		self.open_folder_arr = open_folder_arr
		threading.Thread.__init__(self)

	#
	# Get all method signatures
	#
	def save_method_signature(self, file_name):
		file_lines = open(file_name, 'rU')
		for line in file_lines:
			if "function" in line:
				matches = re.search('(\w+)\s*[: | =]\s*function\s*\((.*)\)', line)
				if matches != None and (len(matches.group(1)) < self.collector.MAX_FUNC_SIZE and len(matches.group(2)) < self.collector.MAX_FUNC_SIZE):
					self.collector.addFunc(matches.group(1), matches.group(2))

	#
	# Get Javascript files paths
	#
	def get_javascript_files(self, dir_name, *args):
		fileList = []
		for file in os.listdir(dir_name):
			dirfile = os.path.join(dir_name, file)
			if os.path.isfile(dirfile):
				fileName, fileExtension = os.path.splitext(dirfile)
				if fileExtension == ".js" and ".min." not in fileName:
					fileList.append(dirfile)
			elif os.path.isdir(dirfile):
				fileList += self.get_javascript_files(dirfile, *args)
		return fileList

	def run(self):
		for folder in self.open_folder_arr:
			jsfiles = self.get_javascript_files(folder)
			for file_name in jsfiles:
				self.save_method_signature(file_name)

	def stop(self):
		if self.isAlive():
			self._Thread__stop()

#
# MySign Collector Class
#
class MySignCollector(MySign, sublime_plugin.EventListener):

	_collector_thread = None

	#
	# Invoked when user save a file
	#
	def on_post_save(self, view):
		self.clear()
		open_folder_arr = view.window().folders()
		if self._collector_thread != None:
			self._collector_thread.stop()
		self._collector_thread = MySignCollectorThread(self, open_folder_arr, 30)
		self._collector_thread.start()
	#
	# Change autocomplete suggestions
	#
	def on_query_completions(self, view, prefix, locations):
		completions = self.get_autocomplete_list(prefix)
		completions = list(set(completions))
		completions.sort()
		if completions:
			return completions