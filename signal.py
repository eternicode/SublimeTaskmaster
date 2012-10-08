"""
http://code.activestate.com/recipes/576477-yet-another-signalslot-implementation-in-python/

File:    signal.py
Author:  Thiago Marcos P. Santos
Created: August 28, 2008

Purpose: A signal/slot implementation
"""

from weakref import WeakValueDictionary


class Signal(object):
    def __init__(self):
        self.__slots = WeakValueDictionary()

    def __call__(self, *args, **kargs):
        for key in self.__slots:
            func, selfid = key
            if selfid is not None:
                func(self.__slots[key], *args, **kargs)
            else:
                func(*args, **kargs)


    def __get_key(self, slot):
        if hasattr(slot, 'im_func'):
            return (slot.im_func, id(slot.im_self))
        else:
            return (slot, None)

    def connect(self, slot):
        key = self.__get_key(slot)
        if hasattr(slot, 'im_func'):
            self.__slots[key] = slot.im_self
        else:
            self.__slots[key] = slot

    def disconnect(self, slot):
        key = self.__get_key(slot)
        if key in self.__slots:
            self.__slots.pop(key)

    def clear(self):
        self.__slots.clear()
