from _travel import Travel
import ctypes
from ctypes import wintypes
import win32con
# from pprint import pprint


if __name__ == '__main__':
    byref = ctypes.byref
    user32 = ctypes.windll.user32

    # NOTE: use same shortcut
    lucky_id = 13425
    lucky_key = 0xBA # ;/:

    if not user32.RegisterHotKey(
            None, lucky_id, win32con.MOD_CONTROL, lucky_key):
        # https://msdn.microsoft.com/en-us/library/ms646309.aspx
        # some variable do not exist in win32con, for example VK_OEM_1
        # you can find valid variables using following code:
        # pprint([key for key in dir(win32con) if key.startswith('VK_')])

        # You may run this script multiple times
        # https://msdn.microsoft.com/en-us/library/dd375731(v=vs.85).aspx
        user32.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        user32.keybd_event(lucky_key, 0, 0, 0)
        user32.keybd_event(lucky_key, 0, win32con.KEYEVENTF_KEYUP, 0)
        user32.keybd_event(
            win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        raise Exception('Failed to register hotkey!')


    # First time show or not show
    app = Travel(is_hidden=False)

    try:
        msg = wintypes.MSG()
        while user32.GetMessageA(byref(msg), None, 0, 0) != 0:
            if not app.is_hidden:
                app.update_idletasks()
                app.update()
            if msg.message == win32con.WM_HOTKEY:
                app._show()
            user32.TranslateMessage(byref(msg))
            user32.DispatchMessageA(byref(msg))
    finally:
        user32.UnregisterHotKey(None, lucky_id)

    # Is multi-thread better?
    # Does my implemention have potential errors?
    # TODO: some error handling may needed,














# from _travel import Travel, BaseScreen
# import Xlib
# from Xlib import X #, XK
# from Xlib.display import Display
# from Xlib.protocol.event import KeyPress, KeyRelease, ClientMessage
# import time as T
# from threading import Thread
# # import gi
# # gi.require_version('Wnck', '3.0')
# # from gi.repository import Wnck

# display = Display()
# # xprop -root _NET_CLIENT_LIST _NET_ACTIVE_WINDOW
# # #xprop -root | grep -E "^_NET_(CLIENT_LIST|ACTIVE_WINDOW)"
# # 0x1400004, 0x1400026, 0x1600003, 0x32000ab, 0x3800010, 0xe00004, 0xe007a7, 0x2000004, 0x3400025, 0x3c00086
# # 'xprop -id {} | grep -E "^(_NET_)?WM_(PID|CLASS|NAME)"'
# # #_NET_WM_ACTION_CLOSE
# # mask = (X.SubstructureRedirectMask|X.SubstructureNotifyMask)
# #334
# win = display.create_resource_object('window', 0x3600017)
# msg = ClientMessage(window=win, client_type=display.intern_atom('WM_DELETE_WINDOW'), data=(32, [1, int(T.time()), 0, 0, 0]))
# win.send_event(msg, propagate=True)
# # display.send_event(win, msg)
# display.flush()
# display.sync()
# display.close()













# import ctypes
# #from ctypes import Structure
# #/usr/lib/x86_64-linux-gnu/libX11
# X11 = ctypes.CDLL('libX11.so.6')


# XID = ctypes.c_ulong
# Bool = ctypes.c_int
# Atom = ctypes.c_ulong
# Window = XID

# class Display(ctypes.Structure):
#     """ opaque struct """

# class _U(ctypes.Union):
#     _fields_ = [
# 	('b', ctypes.c_char * 20),
# 	('s', ctypes.c_short * 10),
# 	('l', ctypes.c_long * 5),
# ]

# class ClientMessage(ctypes.Structure):
#     _fields_ = [
#         ('type', ctypes.c_int),
#         ('serial', ctypes.c_ulong),
#         ('send_event', Bool),
#         ('display', ctypes.POINTER(Display)),
#         ('window', Window),
#         ('message_type', Atom),
#         ('format', ctypes.c_int),
#         ('data', _U),
#     ]


# X11.XOpenDisplay.restype = ctypes.POINTER(Display)
# display = X11.XOpenDisplay(None)
# # root = X11.XDefaultRootWindow(display)

# msg = XClientMessageEvent()

# X11.XInternAtom(display, "WM_PROTOCOLS", True)


# X11.SendEvent(display, 0x3600017, True, 1, ctypes.byref(msg))
# X11.XFlush()
# X11.XCloseDisplay(display)

# # display = X11.XOpenDisplay(None)
# # key = XEvent(type=2).xkey #KeyPress
# # key.keycode = X11.XKeysymToKeycode(display, 0xffcc) #F15
# # key.window = key.root = X11.XDefaultRootWindow(display)
# # X11.XSendEvent(display, key.window, True, 1, ctypes.byref(key))
# # X11.XCloseDisplay(display)


# # class XKeyEvent(ctypes.Structure):
# #     _fields_ = [
# #             ('type', ctypes.c_int),
# #             ('serial', ctypes.c_ulong),
# #             ('send_event', ctypes.c_int),
# #             ('display', ctypes.POINTER(Display)),
# #             ('window', ctypes.c_ulong),
# #             ('root', ctypes.c_ulong),
# #             ('subwindow', ctypes.c_ulong),
# #             ('time', ctypes.c_ulong),
# #             ('x', ctypes.c_int),
# #             ('y', ctypes.c_int),
# #             ('x_root', ctypes.c_int),
# #             ('y_root', ctypes.c_int),
# #             ('state', ctypes.c_uint),
# #             ('keycode', ctypes.c_uint),
# #             ('same_screen', ctypes.c_int),
# #         ]

# # class XEvent(ctypes.Union):
# #     _fields_ = [
# #             ('type', ctypes.c_int),
# #             ('xkey', XKeyEvent),
# #             ('pad', ctypes.c_long*24),
# #         ]

# # class XClientMessageEvent(Structure):
# # 	_fields_ = [
# # 		('type', c_int),
# # 		('serial', c_ulong),
# # 		('send_event', Bool),
# # 		('display', POINTER(Display)),
# # 		('window', Window),
# # 		('message_type', Atom),
# # 		('format', c_int),
# # 		('data', _U),
# # ]
