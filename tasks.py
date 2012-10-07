import os, json

import sublime, sublime_plugin

from settings import TASKLISTS_DIR, STATUSBAR
from signal import Signal

window_tasklists = {}

class TasklistEvents(sublime_plugin.EventListener):
    def filter_events(mth):
        from functools import wraps
        @wraps(mth)
        def wrapped(self, view):
            if view.window() and view.file_name():
                return mth(self, view)
        return wrapped

    loaded = Signal()
    @filter_events
    def on_load(self, view):
        self.loaded(view)

    closed = Signal()
    @filter_events
    def on_close(self, view):
        self.closed(view)

    activated = Signal()
    @filter_events
    def on_activated(self, view):
        self.activated(view)

def get_project(win_id):
    project = None
    reg_session = os.path.join(sublime.packages_path(), "..", "Settings", "Session.sublime_session")
    auto_save = os.path.join(sublime.packages_path(), "..", "Settings", "Auto Save Session.sublime_session")
    session = auto_save if os.path.exists(auto_save) else reg_session

    if not os.path.exists(session) or win_id == None:
        return project

    try:
        with open(session, 'r') as f:
            # Tabs in strings messes things up for some reason
            j = json.JSONDecoder(strict=False).decode(f.read())
            for w in j['windows']:
                if w['window_id'] == win_id:
                    if "workspace_name" in w:
                        if sublime.platform() == "windows":
                            # Account for windows specific formatting
                            project = os.path.normpath(w["workspace_name"].lstrip("/").replace("/", ":/", 1))
                        else:
                            project = w["workspace_name"]
                        break
    except:
        pass

    # Throw out empty project names
    import re
    if project == None or re.match(".*\\.sublime-project", project) == None or not os.path.exists(project):
        project = None

    return project


class Task():
    def __init__(self, title, take_context=False):
        self.title = title
        self.active = False
        self.take_context = take_context
        self.window = None

    def get_data(self):
        return dict(
            title = self.title,
            views = self.views
        )

    @property
    def views(self):
        if self.active:
            return map(self.view_to_dict, self.window.views())
        else:
            return self._views

    @classmethod
    def from_data(cls, data):
        t = cls(data['title'])
        t._views = data['views']
        return t


    def view_to_dict(self, view):
        """
        Converts an active view into a data dict for storage
        """
        return dict(
            file = view.file_name()
        )

    def dict_to_view(self, view):
        """
        Converts a view data dict into a new view
        """
        if not self.window:
            return view

        view = self.window.open_file(view['file'])

        return view

    def add_view(self, view):
        if self.active:
            self.views.append(view)

    def remove_view(self, view):
        if self.active:
            self.views.remove(view)

    def load_view(self, view):
        self.window.open_file(view['file'])

    def activate_on_window(self, window):
        if self.active:
            return

        self.window = window
        self.active = True
        if self.take_context:
            # Import all current views into this task
            self.take_context = False
        else:
            # close all current views
            while self.window.active_view():
                self.window.run_command('close')
            # open new views into current files
            map(self.dict_to_view, self._views)

        # Loading is asynchronous; we add new views to the current task on load.
        # Wait until all activated views are done loading before attaching events.
        def connect_events():
            loading = any(v.is_loading() for v in window.views())
            if loading:
                sublime.set_timeout(connect_events, 100)
            else:
                TasklistEvents.loaded.connect(self.add_view)
                TasklistEvents.closed.connect(self.remove_view)
        sublime.set_timeout(connect_events, 100)

    def deactivate(self):
        self._views = map(self.view_to_dict, self.window.views())
        self.window = None
        self.active = False

        TasklistEvents.loaded.disconnect(self.add_view)
        TasklistEvents.closed.disconnect(self.remove_view)


class TaskList():
    def __init__(self, name, load=False):
        self.name = name
        self.file = os.path.join(TASKLISTS_DIR, name + '.sublime-tasklist')
        self.tasks = []
        self.window = None

        if load:
            self.load()

    def __unicode__(self):
        return self.name
    __str__ = __unicode__


    def exists(self):
        return os.path.exists(self.file)

    def load(self):
        try:
            contents = json.load(open(self.file))
        except IOError:
            return False
        else:
            for tdata in contents['tasks']:
                t = Task.from_data(tdata)
                self.tasks.append(t)
            self._active = contents['active']
            return True

    def save(self, *args):
        if not os.path.exists(TASKLISTS_DIR):
            os.makedirs(TASKLISTS_DIR)
        active = getattr(self.get_active_task(), 'title', None)
        contents = dict(tasks=[], active=active)
        for t in self.tasks:
            contents['tasks'].append(t.get_data())
        json.dump(contents, open(self.file, 'wb'), indent=2)


    def _to_task(self, id):
        if isinstance(id, Task):
            return id if id in self.tasks else None
        elif isinstance(id, basestring):
            ts = filter(lambda t: t.title == id, self.tasks)
            return ts[0] if ts else None
        elif isinstance(id, (int, float)):
            id = int(id)
            return self.tasks[id] if len(self.tasks) > id else None


    @staticmethod
    def get_for_window(window):
        """
        Retrieves the tasklist currently in effect for the given window.
        """
        wid = window.id()
        if wid in window_tasklists:
            return window_tasklists[wid]
        return None

    def save_for_window(self):
        """
        Saves the name of the tasklist currently in effect for the given window.
        """
        if not self.window:
            raise Exception(
                'Tasklist %s has no window' % self
            )
            return

        wid = self.window.id()
        if wid in window_tasklists:
            ctl = window_tasklists[wid]
            raise Exception(
                'Tasklist %s already active on window %s' % (ctl, wid)
            )
        else:
            window_tasklists[wid] = self

    def delete_for_window(self):
        """
        Removes the name of the tasklist from the given window.
        """
        if not self.window:
            raise(
                'Tasklist %s has no window' % self
            )
            return

        wid = self.window.id()
        if window_tasklists.get(wid) is self:
            del window_tasklists[wid]
        else:
            raise(
                'Window %s tasklist mismatch: %s (a) v %s (c)' % (wid, window_tasklists.get(wid), self)
            )


    def clear_statusbars(self):
        if not self.window:
            raise(
                'Tasklist %s has no window' % self
            )
            return

        if not self.window.views() and self.window.active_view():
            self.window.active_view().erase_status(STATUSBAR)
        for v in self.window.views():
            v.erase_status(STATUSBAR)

    def set_statusbars(self):
        if not self.window:
            raise Exception(
                'Tasklist %s has no window' % self
            )
            return


        if not self.window.views() and self.window.active_view():
            self.set_statusbar(self.window.active_view())
        for v in self.window.views():
            self.set_statusbar(v)

    def set_statusbar(self, view, text=None):
        if text is None:
            t = self.get_active_task()
            text = '%(tasklist)s / %(task)s' % {
                        'tasklist': self.name,
                        'task': t.title if t else '-'
                    }

        view.set_status(STATUSBAR, text)


    def activate_on_window(self, window):
        self.window = window
        self.save_for_window()
        if self.tasks:
            if getattr(self, '_active', None):
                self.activate_task(self._active)
                del self._active
            else:
                self.activate_task(0)

        self.set_statusbars()
        TasklistEvents.loaded.connect(self.set_statusbar)
        TasklistEvents.loaded.connect(self.save)
        TasklistEvents.closed.connect(self.save)
        TasklistEvents.activated.connect(self.save)

    def deactivate(self):
        self.clear_statusbars()
        self.delete_for_window()
        self.window = None

    def add_task(self, task, activate=False):
        assert task

        self.tasks.append(task)
        if activate:
            self.activate_task(task)

    def activate_task(self, task):
        if not self.window:
            raise Exception(
                'Tasklist %s has no window' % self
            )

        t = self._to_task(task)
        if not t:
            raise Exception(
                'Tasklist %s has no task identifiable with "%s"' % (self, task)
            )

        self.tasks.remove(t)
        self.tasks.insert(0, t)
        ct = self.get_active_task()
        if ct == t:
            return
        if ct:
            ct.deactivate()
        t.activate_on_window(self.window)
        self.set_statusbars()

    def deactivate_tasks(self):
        for t in self.tasks:
            if t.active:
                t.deactivate()

    def get_active_task(self):
        for t in self.tasks:
            if t.active:
                return t


