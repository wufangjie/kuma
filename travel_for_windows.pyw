from _travel import Travel, BaseScreen, Message
import ctypes
from ctypes import wintypes
import win32gui, win32con
import win32com.client
import win32process
import win32api
import psutil
# from pprint import pprint


# FIXME: windows call emacs from kuma will not load .emacs
# FIXME: keyword "setting" only can activate, can not open setting yet
# The knowledge of window style and exstyle may help a lot
# https://msdn.microsoft.com/en-us/library/windows/desktop/ff700543(v=vs.85).aspx
# https://msdn.microsoft.com/en-us/library/windows/desktop/ms632600(v=vs.85).aspx



class WindowsScreen(BaseScreen):
    """GetClassName is not good enough, but I have no better idea"""
    def get_windows(self):
        def valid(hWnd, param):
            if (win32gui.IsWindow(hWnd)
                and win32gui.IsWindowEnabled(hWnd)
                and win32gui.IsWindowVisible(hWnd)
            ):
                style = win32gui.GetWindowLong(hWnd, win32con.GWL_EXSTYLE)
                if not (style & 0x08000080) and style != 0x00200000:
                    hWnds.append(hWnd)

        hWnds, ret = [], []
        win32gui.EnumWindows(valid, 0)
        dct = {p.pid: p for p in psutil.process_iter()}
        for hWnd in hWnds:
            text = win32gui.GetWindowText(hWnd)
            if text:
                tid, pid = win32process.GetWindowThreadProcessId(hWnd)
                app = dct[pid].name()
                if app.endswith('.exe'):
                    app = app[:-4]
                # win32gui.GetClassName is not good enough
                ret.append((app, str(pid), text, hWnd))

        self.current_window = win32gui.GetActiveWindow()
        return ret

    def activate_window(self, hWnd):
        """
        FIXME: this function may not bring window to topmost sometimes
        """
        is_previous_disable = win32gui.EnableWindow(hWnd, True)
        # see window style WS_DISABLED
        # A disabled window cannot receive input from the user
        win32com.client.Dispatch('WScript.Shell').SendKeys('^')#%')
        # must send key, someone says it's a pywin32 bug
        win32gui.SetForegroundWindow(hWnd)
        if is_previous_disable:
            win32gui.EnableWindow(hWnd, False)

    def close_window(self, hWnd):
        """
        DestroyWindow() can only be called by the thread that created the window
        """
        # win32gui.SendMessage(hWnd, win32con.WM_CLOSE)
        # WM_DESTROY did not work
        try:
            win32gui.PostMessage(hWnd, win32con.WM_CLOSE)
        except Exception as e:
            pid = win32process.GetWindowThreadProcessId(hWnd)[1]
            handle = win32api.OpenProcess(win32con.PROCESS_TERMINATE, 0, pid)
            if handle:
                win32api.TerminateProcess(handle, 0)
                win32api.CloseHandle(handle)
            else:
                self.activate_window(hWnd)



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

        # To prevent you run this script multiple times
        # https://msdn.microsoft.com/en-us/library/dd375731(v=vs.85).aspx
        user32.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        user32.keybd_event(lucky_key, 0, 0, 0)
        user32.keybd_event(lucky_key, 0, win32con.KEYEVENTF_KEYUP, 0)
        user32.keybd_event(
            win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        raise Exception('Failed to register hotkey!')

    # First time show or not show
    app = Travel(WindowsScreen(), is_hidden=False)

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
