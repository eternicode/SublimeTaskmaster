import os

import sublime

settings = sublime.load_settings('Taskmaster.sublime-settings')
TASKLISTS_DIR = os.path.expanduser('~/.sublime/taskmaster/')
STATUSBAR = 'statusbar_taskmaster'
