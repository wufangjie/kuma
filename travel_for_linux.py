#!/usr/bin/python3
# -*- coding: utf-8 -*-

from _travel import Travel, BaseScreen, main
from PyQt5.QtCore import pyqtSignal, QThread
import Xlib
from Xlib import X #, XK
from Xlib.display import Display
# from Xlib.protocol.event import KeyPress, KeyRelease, ClientMessage
#import time
#from threading import Thread
import subprocess
import re
#import sys


reg_xid = re.compile(r'(0x[0-9a-f]+)')

disp = Display()
CLASS = disp.intern_atom('WM_CLASS')
TITLE = disp.intern_atom('_NET_WM_NAME')
# PID = disp.intern_atom('_NET_WM_PID') # not guaranteed
# NOTE: As far as I can see, CLASS is good enough


def send_event(detail, state, root, display, child=X.NONE,
               same_screen=1, root_x=0, root_y=0, event_x=0, event_y=0):
    """This send event discourage me a lot"""
    # time = int(time.time()) # X.CurrentTime
    # window = root # display.get_input_focus().focus
    # params = locals()
    # params.pop('display')
    # # return KeyPress(**params)
    # window.send_event(KeyPress(**params), event_mask=1, propagate=True)
    # display.flush()
    # window.send_event(KeyRelease(**params), event_mask=1, propagate=True)
    # display.flush()
    pass


def get_property_string(win, typ):
    # on xubuntu 18.04, ret will be bytes rather than string
    try:
        ret = win.get_full_property(typ, 0).value
    except Exception as e:
        return ''
    if isinstance(ret, bytes):
        return ret.decode('utf-8')
    else:
        return str(ret)


class LinuxScreen(BaseScreen):
    """I do not use multi-workspace"""
    def get_windows(self):
        temp = subprocess.check_output(
            'xprop -root _NET_ACTIVE_WINDOW _NET_CLIENT_LIST',
            shell=True).decode('utf-8').split('\n')

        try:
            kuma = eval(reg_xid.findall(temp[0])[0])
            xids = {eval(xid) for xid in reg_xid.findall(temp[1])}
            xids.discard(kuma)
            self.current_window = disp.create_resource_object('window', kuma)
        except Exception as e:
            return []

        ret = []
        for xid in xids:
            try:
                win = disp.create_resource_object('window', xid)
                app = get_property_string(win, CLASS).split('\x00')
                if len(app) > 1 and app[1] not in {'Xfce4-panel', 'Xfdesktop'}:
                    title = get_property_string(win, TITLE)
                    ret.append((app[1], title, win.id, win))
            except Exception as e:
                pass
        return ret

    def activate_window(self, hw):
        hw.raise_window()
        disp.sync()

    def close_window(self, hw):
        # FIXME: synaptic will crush when start next time,
        # then you should click to let it disappear, then start again
        # Or we should use activate, then Alt + F4 to close it
        hw.destroy()
        disp.sync()


if __name__ == '__main__':
    kuma = Travel(LinuxScreen())

    display = Display()
    root = display.screen().root
    root.change_attributes(event_mask=X.KeyPressMask)

    # Control + ; (and maybe Caps Lock, Num Lock)
    # TODO: add hotkey config like windows way
    key = 47
    mods = [0x0004, 0x0006, 0x0014, 0x0016]

    for mod in mods:
        root.grab_key(key, mod, True, X.GrabModeAsync, X.GrabModeAsync)

    # print(display.no_operation())
    # send_event(key, mods[0], root)
    # # XPending, XNextEvent, XWindowEvent
    # # pending_events, next_event,
    # raise Exception


    def error_handler(*args, **kwargs):
        """I can not find a detailed document about Error Handling"""
        kuma.running = False

    display.set_error_handler(error_handler)

    # X protocol error: <class 'Xlib.error.BadAccess'>
    # means a confliction, other client has grab the same key combination

    # NOTE: grab_key won't tell anything about the conflication
    # I tryed onerror params, but did not work
    # error only happens when run display.next_event()

    class Listen(QThread):
        _show = pyqtSignal(name='show')

        def run(self):
            try:
                while True:
                    event = display.next_event()
                    if not kuma.running:
                        break
                    if event.type == 2:
                        self._show.emit()
            finally:
                for mod in mods:
                    root.ungrab_key(key, mod)
                display.close()

    main(kuma, Listen())
