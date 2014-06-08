#-----------------------------------------------------------------------------------
# MySignature Sublime Text Plugin
# Author: Elad Yarkoni
# Version: 1.0
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

	def clear(self):
		self.files = dict()

	def save_functions(self, file, data):
		self.files[file] = data
		if debug:
			print(self.files[file])

	def get_completions(self, prefix):
		skip_deleted = Pref.forget_deleted_files
		completions = []
		for file, data in self.files.items():
			if not skip_deleted or (skip_deleted and os.path.lexists(file)):
				location = basename(file)
				for function in data:
					if prefix in function['name']:
						name = function['name'] + '(' + function['sign']+ ')'
						if 'hint' not in function:
							function['hint'] = ", ".join(["${%s:%s}" % (k+1, v.strip()) for k, v in enumerate(function['sign'].split(','))])

						completions.append((name + '\t' + location, function['name'] + '(' + function['hint']+')'))
		if debug:
			print("Completions")
			print(completions)
		return completions

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
		else:
			# the list of opened files in all the windows
			files = [norm_path(v.file_name()) for window in sublime.windows() for v in window.views() if v.file_name() and is_javascript_file(v.file_name()) and not should_exclude(norm_path(v.file_name()))]
			# the list of opened folders in all the windows
			folders = [norm_path(folder) for window in sublime.windows() for folder in window.folders() if folder and not should_exclude(norm_path(folder))]
			Pref.folders = list(folders) # this is the "cache id" to know when to rescan the whole thing again
			# add also as folders, the dirname of the current opened files
			folders += [norm_path(dirname(file)) for file in files]

			folders = list(set(folders))
			if debug:
				print('Folders to scan:')
				print("\n".join(folders))
			for folder in folders:
				self.get_files(folder, files)

			files = list(set(files))
			if debug:
				print('Files to parse:')
				print("\n".join(files))

			for file in files:
				if file not in MySign.files:
					try:
						self.parse_functions(file)
					except:
						pass # the file may be unreachable/unreadable
				else:
					if debug:
						print('Skipping parsing of already indexed file')

	def parse_functions(self, file):
		if debug:
			print('\nParsing functions for file:\n'+file)
		lines = [line for line in codecs.open(file, encoding='utf8') if len(line) < 300 and "function" in line]
		functions = []
		for line in lines:
			for regexp in Pref.expressions:
				matches = regexp(line)
				if matches and matches.groupdict() not in functions:
					functions.append(matches.groupdict())
					break
		MySign.save_functions(file, functions)

	def get_files(self, dir, files):
		for file in os.listdir(dir):
			file = os.path.join(dir, file)
			if os.path.isfile(file) and not should_exclude(file):
				if is_javascript_file(file):
					files.append(norm_path(file))
			elif os.path.isdir(file) and not should_exclude(file):
				self.get_files(file, files)

class MySignEventListener(sublime_plugin.EventListener):

	def on_post_save_async(self, view):
		if is_javascript_view(view):
			MySignCollectorThread(view.file_name()).start()

	def on_load_async(self, view):
		if is_javascript_view(view) and is_javascript_file(view.file_name()):
			if norm_path(view.file_name()) not in MySign.files: # only if it is not indexed
				MySignCollectorThread(view.file_name()).start()

	def on_query_completions(self, view, prefix, locations):
		if is_javascript_view(view, locations):
			return MySign.get_completions(prefix)
		return ([], sublime.INHIBIT_EXPLICIT_COMPLETIONS)

global Pref, s

def is_javascript_view(view, locations = None):
	return (view.file_name() and is_javascript_file(view.file_name())) or ('JavaScript' in view.settings().get('syntax')) or ( locations and len(locations) and '.js' in view.scope_name(locations[0]))

def is_javascript_file(file):
	return file.endswith('.js') and '.min.' not in file

def norm_path(file):
	return normcase(normpath(realpath(file))).replace('\\', '/')

def norm_path_string(file):
	return file.strip().lower().replace('\\', '/').replace('//', '/')

def should_exclude(file):
	return len([1 for exclusion in Pref.excluded_files_or_folders if exclusion in file])

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
			'(?P<name>\w+)\s*[: | =]\s*function\s*\((?P<sign>[^\)]*)\)',
			'function\s*(?P<name>\w+)\s*\((?P<sign>[^\)]*)\)'
		]]
		Pref.folders = []

		MySign.clear()
		MySignCollectorThread().start()


def folder_change_watcher():
	while True:
		time.sleep(5)
		folders = [norm_path(folder) for window in sublime.windows() for folder in window.folders() if folder and not should_exclude(norm_path(folder))]
		folders = list(set(folders))
		folders.sort()

		Pref.folders = list(set(Pref.folders))
		Pref.folders.sort()
		if Pref.folders != folders:
			MySignCollectorThread().start()


def plugin_loaded():
	global Pref, s
	s = sublime.load_settings('MySignaturePlugin.sublime-settings')
	Pref = Pref()
	Pref.load()
	s.clear_on_change('reload')
	s.add_on_change('reload', lambda:Pref.load())

	if not 'running_folder_change_watcher' in globals():
		running_folder_change_watcher = True
		thread.start_new_thread(folder_change_watcher, ())

if int(sublime.version()) < 3000:
	plugin_loaded()