from _travel import Travel, BaseScreen, LazyApp
import Xlib
from Xlib import X #, XK
from Xlib.display import Display
# from Xlib.protocol.event import KeyPress, KeyRelease, ClientMessage
import time as T
from threading import Thread
import subprocess
import re


reg_xid = re.compile(r'(0x[0-9a-f]+)')

disp = Display()
CLASS = disp.intern_atom('WM_CLASS')
TITLE = disp.intern_atom('_NET_WM_NAME')
# PID = disp.intern_atom('_NET_WM_PID') # not guaranteed
# NOTE: As far as I can see, CLASS is good enough



def send_event(detail, state, root, display, child=X.NONE,
               same_screen=1, root_x=0, root_y=0, event_x=0, event_y=0):
    """This send event discourage me a lot"""
    # time = int(T.time()) # X.CurrentTime
    # window = root # display.get_input_focus().focus
    # params = locals()
    # params.pop('display')
    # # return KeyPress(**params)
    # window.send_event(KeyPress(**params), event_mask=1, propagate=True)
    # display.flush()
    # window.send_event(KeyRelease(**params), event_mask=1, propagate=True)
    # display.flush()
    pass



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
                app = str(win.get_full_property(CLASS, 0).value).split('\x00')
                if app[1] not in {'Xfce4-panel', 'Xfdesktop'}:
                    title = str(win.get_full_property(TITLE, 0).value)
                    ret.append((app[1], '', title, win))
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
    app = LazyApp()

    display = Display()
    root = display.screen().root
    root.change_attributes(event_mask=X.KeyPressMask)

    # Control + ; (and maybe Caps Lock, Num Lock)
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
        app.running = False

    display.set_error_handler(error_handler)

    # X protocol error: <class 'Xlib.error.BadAccess'>
    # means a confliction, other client has grab the same key combination

    # NOTE: grab_key won't tell anything about the conflication
    # I tryed onerror params, but did not work
    # error only happens when run display.next_event()

    def listen():
        try:
            while True:
                event = display.next_event()
                # print(event.__dict__)
                if not app.running:
                    break
                if event.type == 2:
                    app._show()
        finally:
            for mod in mods:
                root.ungrab_key(key, mod)
            display.close()


    t = Thread(target=listen)
    t.start()
    T.sleep(0.1)

    if app.running:
        # single kuma guranteed
        app.update(Travel(LinuxScreen(), is_hidden=True))
        app.app.mainloop()
        app.running = False
        disp.close()

        # # close display can not terminate thread
        # for mod in mods:
        #     root.ungrab_key(key, mod)
        # display.close()

        # omit flush will not send event,
        # but with flush will crash the whole input system
        send_event(key, mods[0], root, display)

        # T.sleep(1)
        t.join()
    else:
        raise Exception(
            'Key confliction detected, maybe another kuma is running')




################################################################################
# # abandon
################################################################################

# xprop -root _NET_CLIENT_LIST _NET_ACTIVE_WINDOW

# xprop -id {} | grep -E "^(_NET_)?WM_(PID|CLASS|NAME)"'
# xprop -id {} _WM_CLASS _NET_WM_NAME


# display = Display()
# root = display.screen().root
# win = display.create_resource_object('window', 0x32000ab)


# Send event

# mask = X.SubstructureRedirectMask | X.SubstructureNotifyMask
# # # should send to the root
# # msg = ClientMessage(window=win,
# #                     client_type=display.intern_atom('_NET_ACTIVE_WINDOW'),#'WM_DELETE_WINDOW'),
# #                     data=(32, [1, 0, 0, 0, 0])) #int(T.time())


# # should send to the root
# msg = ClientMessage(window=win,
#                     client_type=display.intern_atom('_NET_CLOSE_WINDOW'),#'WM_DELETE_WINDOW'),
#                     data=(32, [int(T.time()), 1, 0, 0, 0])) #int(T.time())
# display.send_event(root, msg)
# display.flush()
# display.sync()
# # display.close()

# display.send_event(root, msg)
# display.flush()
# display.sync()
# # display.close()


# for wid in [0x1400004, 0x1400026, 0x1600003, 0x32000ab, 0x5000025, 0xe55fa7, 0xe56b8c, 0x3000021, 0xe5e2d5]:
#     print(wid)
#     print(subprocess.check_output('xprop -id {} | grep -E "^(_NET_)?WM_(PID|CLASS|NAME)"'.format(wid), shell=True).decode('utf-8'))
