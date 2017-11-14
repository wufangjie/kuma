from _travel import create_app
import Xlib
from Xlib import X, XK
from Xlib.display import Display
from Xlib.protocol.event import KeyPress, KeyRelease
import time as T
from threading import Thread
# from multiprocessing import Process


def send_event(detail, state, root, display, child=X.NONE,
               same_screen=1, root_x=0, root_y=0, event_x=0, event_y=0):
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


class LazyApp:
    def __init__(self):
        self.app = None
        self.running = True

    def _show(self):
        if self.app:
            self.app._show()

    def update(self, app):
        self.app = app


if __name__ == '__main__':
    display = Display()
    root = display.screen().root
    root.change_attributes(event_mask=X.KeyPressMask)

    # Control + ' (and maybe Caps Lock, Num Lock)
    key = 47
    mods = [0x0004, 0x0006, 0x0014, 0x0016]

    for mod in mods:
        root.grab_key(key, mod, True, X.GrabModeAsync, X.GrabModeAsync)

    # print(display.no_operation())
    # send_event(key, mods[0], root)
    # # XPending, XNextEvent, XWindowEvent
    # # pending_events, next_event,
    # raise Exception



    app = LazyApp()

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
        app.update(create_app(is_hidden=True))
        app.app.mainloop()
        app.running = False

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

    # send_event(key, mods[0], root)
    # # XPending, XNextEvent, XWindowEvent
    # # pending_events, next_event,
    # raise Exception
