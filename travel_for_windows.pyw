from _travel import Travel, BaseScreen, LazyApp
import ctypes
from ctypes import wintypes
import win32gui, win32con
import win32com.client
import win32process
import win32api
import psutil
from threading import Thread
import time as T


# FIXME: windows call emacs from kuma will not load .emacs
# NOTE: kuma can not activate a minimized task manager, maybe it's a win32api bug
# I checked some other applications with the same STYLE and EXSTYLE, work well
# And I find run the command (try to start a new one) works, but it is not elegant
# So I think if you find kuma can not activate a task manager,
# just use system's shortcut (win + x t, or control + shift + esc) to activate,
# or never minimize a task manager

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
        self.current_window = win32gui.GetActiveWindow()
        win32gui.EnumWindows(valid, 0)
        dct = {p.pid: p for p in psutil.process_iter()}
        for hWnd in hWnds:
            if hWnd != self.current_window:
                text = win32gui.GetWindowText(hWnd)
                if text:
                    tid, pid = win32process.GetWindowThreadProcessId(hWnd)
                    app = dct[pid].name()
                    if app.endswith('.exe'):
                        app = app[:-4]
                    # win32gui.GetClassName is not good enough
                    ret.append((app, str(pid), text, hWnd))
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

        style = win32gui.GetWindowLong(hWnd, win32con.GWL_STYLE)
        if style & win32con.WS_MINIMIZE:
            win32gui.ShowWindow(hWnd, win32con.SW_RESTORE)
            # win32gui.SetWindowLong()'s position is negative
            # win32gui.SetWindowPos() can not get origin position
        else:
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
    app = LazyApp()

    byref = ctypes.byref
    user32 = ctypes.windll.user32

    # NOTE: use same shortcut
    lucky_id = 13425
    lucky_key = 0xBA # ;/:

    def send_hotkey():
        # https://msdn.microsoft.com/en-us/library/dd375731(v=vs.85).aspx
        user32.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        user32.keybd_event(lucky_key, 0, 0, 0)
        user32.keybd_event(lucky_key, 0, win32con.KEYEVENTF_KEYUP, 0)
        user32.keybd_event(
            win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)


    def listen():
        # must register in the thread
        # https://msdn.microsoft.com/en-us/library/ms646309.aspx
        # some variable do not exist in win32con, for example VK_OEM_1
        # you can check valid variables using following code:
        # pprint([key for key in dir(win32con) if key.startswith('VK_')])
        if not user32.RegisterHotKey(
                None, lucky_id, win32con.MOD_CONTROL, lucky_key):
            return send_hotkey()
        try:
            msg = wintypes.MSG()
            while user32.GetMessageA(byref(msg), None, 0, 0) != 0:
                if msg.message == win32con.WM_HOTKEY:
                    app._show()
                user32.TranslateMessage(byref(msg))
                user32.DispatchMessageA(byref(msg))
                if not app.running:
                    break
        finally:
            user32.UnregisterHotKey(None, lucky_id)

    t = Thread(target=listen)
    t.start()
    T.sleep(0.1)

    if t.is_alive():
        app.update(Travel(WindowsScreen(), is_hidden=False))
        app.app.mainloop()
        app.running = False
        send_hotkey()
        t.join()

    # If I do not use multi-thread, then the cursor will not blink
    # Does my implemention have potential errors?
    # TODO: some error handling may needed,

    # try:
    #     msg = wintypes.MSG()
    #     while user32.GetMessageA(byref(msg), None, 0, 0) != 0:
    #         if not app.is_hidden:
    #             app.update_idletasks()
    #             app.update()
    #         if msg.message == win32con.WM_HOTKEY:
    #             app._show()
    #         user32.TranslateMessage(byref(msg))
    #         user32.DispatchMessageA(byref(msg))
    # finally:
    #     user32.UnregisterHotKey(None, lucky_id)
