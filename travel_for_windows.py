from travel import Travel, create_root
import ctypes
from ctypes import wintypes
import win32con
# from pprint import pprint


class TravelNotDestroy(Travel):
    def _destroy(self):
        self._hide()


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
    app = TravelNotDestroy(create_root(), False)

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
