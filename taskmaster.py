import os

import sublime, sublime_plugin

from settings import TASKLISTS_DIR
from tasks import Task, TaskList


class NewTasklistCommand(sublime_plugin.WindowCommand):
  def run(self, name=None):
    def create_tasklist(name):
        tl = TaskList(name)
        if tl.exists():
            sublime.status_message('A tasklist by that name already exists')
        else:
            tl.save()
            sublime.run_command('open_tasklist', {'tasklist': tl.name})

    if name is None:
        self.window.show_input_panel("New tasklist name", "", create_tasklist, None, None)
    else:
        create_tasklist(name)


class OpenTasklistCommand(sublime_plugin.WindowCommand):
  def run(self, tasklist=None):
    def activate_tasklist(ix):
        name = tasklists[ix]
        if ctl and ctl.name != name:
            ctl.deactivate()
        if not ctl or ctl.name != name:
            tl = TaskList(name, load=True)
            tl.activate_on_window(self.window)

    ctl = TaskList.get_for_window(self.window)

    tasklists = os.listdir(TASKLISTS_DIR)
    tasklists = filter(lambda f: f.endswith('.sublime-tasklist'), tasklists)
    tasklists = map(lambda f: os.path.basename(f).replace('.sublime-tasklist', ''), tasklists)

    if tasklist is None:
        self.window.show_quick_panel(tasklists, activate_tasklist)
    else:
        activate_tasklist(tasklists.index(tasklist))


class CloseTasklistCommand(sublime_plugin.WindowCommand):
  def run(self):
    ctl = TaskList.get_for_window(self.window)
    ctl.deactivate()


class NewTaskCommand(sublime_plugin.WindowCommand):
    def run(self, title=None):
        tl = TaskList.get_for_window(self.window)
        if not tl:
            sublime.status_message(
                'No active tasklist found; activate or create a tasklist before '
                'creating tasks'
            )
            return

        def create_task(title):
            t = Task(title, take_context=True)
            tl.add_task(t, activate=True)

        if title is None:
            self.window.show_input_panel("New task title", "", create_task, None, None)
        else:
            create_task(title)


class OpenTaskCommand(sublime_plugin.WindowCommand):
    def run(self):
        ctl = TaskList.get_for_window(self.window)
        if not ctl:
            sublime.status_message(
                'No active tasklist found; activate or create a tasklist before '
                'opening tasks'
            )
            return

        tasks = map(lambda t: t.title, ctl.tasks)

        def open_task(ix):
            title = tasks[ix]
            ctl.activate_task(title)

        self.window.show_quick_panel(tasks, open_task)
