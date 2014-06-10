# coding=utf8
#-----------------------------------------------------------------------------------
# MySignature Sublime Text Plugin
# Author: Elad Yarkoni
# Contributor: Tito Bouzout <tito.bouzout@gmail.com>
# Version: 2.0
# Description: Sublime text autocomplete improvements:
#				- showing javascript methods with parameters
#-----------------------------------------------------------------------------------
import sublime, sublime_plugin, os, re, threading, codecs, time
from os.path import basename, dirname, normpath, normcase, realpath

try:
	import thread
except:
	import _thread as thread


global debug
debug = False

class MySign:

	files = dict()

	NAME = 'name'
	SIGN = 'sign'
	COMPLETION = 'completion'

	EMPTY = ''

	def clear(self):
		self.files = dict()

	def save_functions(self, file, data):
		self.files[file] = data
		if debug:
			print(self.files[file])

	def get_completions(self, view, prefix):
		skip_deleted = Pref.forget_deleted_files

		# start with default completions
		completions = list(Pref.always_on_auto_completions)

		# append these from indexed files
		already_in = []
		for file, data in self.files.items():
			if not skip_deleted or (skip_deleted and os.path.lexists(file)):
				location = basename(file)
				for function in data:
					if prefix in function[self.NAME]:
						already_in.append(function[self.NAME])
						completion = self.create_function_completion(function, location)
						completions.append(completion)

		# current file
		location = basename(view.file_name()) if view.file_name() else '';

		# append functions from current view that yet have not been saved
		[completions.append(self.create_function_completion(self.parse_line(view.substr(view.line(selection))), location)) for selection in view.find_by_selector('entity.name.function') if view.substr(selection) not in already_in and (already_in.append(view.substr(selection)) or True)]

		# append "var" names from current file
		vars = []; [view.substr(selection) for selection in view.find_all('([var\s+]|\.)(\w+)\s*[=|:]', 0, '$2', vars)]
		[completions.append(self.create_var_completion(var, location)) for var in list(set(vars)) if len(var) > 1 and var not in already_in]

		if debug:
			print("Completions")
			print(completions)
		return completions

	def create_function_completion(self, function, location):
		if self.COMPLETION not in function:
			name = function[self.NAME] + '(' + function[self.SIGN]+ ')'
			if function[self.SIGN].strip() == self.EMPTY:
				hint = self.EMPTY
			else:
				hint = ", ".join(["${%s:%s}" % (k+1, v.strip()) for k, v in enumerate(function[self.SIGN].split(','))])
			function[self.COMPLETION] = (name + '\t' + location, function[self.NAME] + '(' + hint+')')
			del function[self.SIGN] # no longer needed
		return function[self.COMPLETION]

	def create_var_completion(self, var, location):
		return (var + '\t' + location, var)

	def parse_line(self, line):
		for regexp in Pref.expressions:
			matches = regexp(line)
			if matches:
				return matches.groupdict()

MySign = MySign()

# the thread will parse or reparse a file if the file argument is present
# if the "file" argument is not present, then will rescan the folders
class MySignCollectorThread(threading.Thread):

	def __init__(self, file = None):
		self.file = file
		threading.Thread.__init__(self)

	def run(self):
		if self.file:
			try:
				self.parse_functions(norm_path(self.file))
			except:
				pass
		elif not Pref.scan_running:
			Pref.scan_running = True
			Pref.scan_started = time.time()

			# the list of opened files in all the windows
			files = list(Pref.updated_files)
			# the list of opened folders in all the windows
			folders = list(Pref.updated_folders)
			Pref.folders = list(folders) # this is the "cache id" to know when to rescan the whole thing again
			# add also as folders, the dirname of the current opened files
			folders += [norm_path(dirname(file)) for file in files]
			# deduplicate
			folders = list(set(folders))
			_folders = []
			for folder in folders:
				_folders = deduplicate_crawl_folders(_folders, folder)
			folders = _folders

			if debug:
				print('Folders to scan:')
				print("\n".join(folders))

			# pasing
			files_seen = 0
			files_js = 0
			files_cache_miss = 0
			files_cache_hit = 0
			files_failed_parsing = 0

			# parse files with priority
			for file in files:
				if should_abort():
					break
				files_seen += 1
				files_js += 1
				if file not in MySign.files:
					try:
						self.parse_functions(file)
						files_cache_miss += 1
					except:
						files_failed_parsing += 1# the file may be unreachable/unreadable
				else:
					files_cache_hit += 1

			# now parse folders
			for folder in folders:
				if should_abort():
					break
				for dir, dnames, files in os.walk(folder):
					if should_abort():
						break
					for f in files:
						if should_abort():
							break
						files_seen += 1
						file = os.path.join(dir, f)
						if not should_exclude(file) and is_javascript_file(file):
							files_js += 1
							file = norm_path(file)
							if file not in MySign.files:
								try:
									self.parse_functions(file)
									files_cache_miss += 1
								except:
									files_failed_parsing += 1# the file may be unreachable/unreadable
							else:
								files_cache_hit += 1

			if debug:
				print('Scan done in '+str(time.time()-Pref.scan_started)+' seconds - Scan was aborted: '+str(Pref.scan_aborted))
				print('Files Seen:'+str(files_seen)+', Files JS:'+str(files_js)+', Cache Miss:'+str(files_cache_miss)+', Cache Hit:'+str(files_cache_hit)+', Failed Parsing:'+str(files_failed_parsing))

			Pref.scan_running = False
			Pref.scan_aborted = False

	def parse_functions(self, file):
		if debug:
			print('\nParsing functions for file:\n'+file)
		lines = [line for line in codecs.open(file, encoding='utf8', errors='replace') if len(line) < 300 and "function" in line]
		functions = []
		for line in lines:
			matches = MySign.parse_line(line)
			if matches and matches not in functions:
				functions.append(matches)
		MySign.save_functions(file, functions)

class MySignEventListener(sublime_plugin.EventListener):

	def on_post_save(self, view):
		if is_javascript_view(view):
			MySignCollectorThread(view.file_name()).start()

	def on_load(self, view):
		if is_javascript_view(view) and is_javascript_file(view.file_name()):
			if norm_path(view.file_name()) not in MySign.files: # only if it is not indexed
				MySignCollectorThread(view.file_name()).start()

	def on_activated(self, view):
		update_folders()

	def on_query_completions(self, view, prefix, locations):
		if is_javascript_view(view, locations):
			return (MySign.get_completions(view, prefix), 0)
		return ([], 0)

global Pref, s

Pref = {}
s = {}

def is_javascript_view(view, locations = None):
	return (view.file_name() and is_javascript_file(view.file_name())) or ('JavaScript' in view.settings().get('syntax')) or ( locations and len(locations) and '.js' in view.scope_name(locations[0]))

def is_javascript_file(file):
	return file and file.endswith('.js') and '.min.' not in file

def norm_path(file):
	return normcase(normpath(realpath(file))).replace('\\', '/')

def norm_path_string(file):
	return file.strip().lower().replace('\\', '/').replace('//', '/')

def should_exclude(file):
	return len([1 for exclusion in Pref.excluded_files_or_folders if exclusion in file])

def update_folders():
	folders = list(set([norm_path(folder) for w in sublime.windows() for folder in w.folders() if folder and not should_exclude(norm_path(folder))]))
	_folders = []
	for folder in folders:
		_folders = deduplicate_crawl_folders(_folders, folder)
	_folders.sort()
	Pref.updated_folders = _folders
	Pref.updated_files = [norm_path(v.file_name()) for w in sublime.windows() for v in w.views() if v.file_name() and is_javascript_file(v.file_name()) and not should_exclude(norm_path(v.file_name()))]

def should_abort():
	if time.time() - Pref.scan_started > Pref.scan_timeout:
		Pref.scan_aborted = True
	return Pref.scan_aborted

# returns folders without child subfolders
def deduplicate_crawl_folders(items, item):
	new_list = []
	add = True
	for i in items:
		if i.find(item+'\\') == 0 or i.find(item+'/') == 0:
			continue
		else:
			new_list.append(i)
		if (item+'\\').find(i+'\\') == 0 or (item+'/').find(i+'/') == 0:
			add = False
	if add:
		new_list.append(item)
	return new_list

class Pref():

	def load(self):
		if debug:
			print('-----------------')
		Pref.excluded_files_or_folders = [norm_path_string(file) for file in s.get('excluded_files_or_folders', [])]
		if debug:
			print('excluded_files_or_folders')
			print(Pref.excluded_files_or_folders)

		Pref.forget_deleted_files = s.get('forget_deleted_files', False)

		Pref.expressions = [re.compile(v, re.U).search for v in [
			'(?P<name>\w+)\s*[:|=]\s*function\s*\((?P<sign>[^\)]*)\)',
			'function\s*(?P<name>\w+)\s*\((?P<sign>[^\)]*)\)'
		]]
		Pref.folders = []

		Pref.always_on_auto_completions = [(re.sub('\${[^}]+}', 'aSome', w), w) for w in s.get('always_on_auto_completions', [])]

		Pref.scan_running = False # to avoid multiple scans at the same time
		Pref.scan_aborted = False # for debuging purposes
		Pref.scan_started = 0
		Pref.scan_timeout = 60 # seconds

		update_folders()

		MySign.clear()
		MySignCollectorThread().start()

def MySign_folder_change_watcher():
	while True:
		time.sleep(5)
		if not Pref.scan_running and Pref.updated_folders != Pref.folders:
			MySignCollectorThread().start()

def plugin_loaded():
	global Pref, s
	s = sublime.load_settings('MySignaturePlugin.sublime-settings')
	Pref = Pref()
	Pref.load()
	s.clear_on_change('reload')
	s.add_on_change('reload', lambda:Pref.load())

	if not 'running_MySign_folder_change_watcher' in globals():
		running_MySign_folder_change_watcher = True
		thread.start_new_thread(MySign_folder_change_watcher, ())

if int(sublime.version()) < 3000:
	sublime.set_timeout(lambda:plugin_loaded(), 0)