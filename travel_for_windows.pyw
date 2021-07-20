import logging
from _travel import Travel, BaseScreen, main
from PyQt5.QtCore import pyqtSignal, QThread
import ctypes
from ctypes import wintypes
import win32gui
import win32con
import win32com.client
import win32process
import win32api
#from threading import Thread
#import time
# import subprocess
import sys
import os
import logging
logger = logging.getLogger(__name__)
import json


# NOTE: kuma can not activate a minimized task manager or register...
# It's a UIPI (User Interface Privilege Isolation) problem
# You can solve it following ways:
# 1. give kuma the admin privilege
# 2. (1) set UAC to the lowest level
#    (2) compile give_me_admin_privilege.cs with .net's csc.exe and give it admin privilege
#    (3) uncomment subprocess code
#    NOTE: every time use admin privilege will appear a splash console
# 3. run the command (try to start a new one) rather activate, but it is only work on the application in config.org
# 4. just use system's shortcut (win + x t, or control + shift + esc) to activate,
# 5. never minimize a task manager

# The knowledge of window style and exstyle may help a lot
# https://msdn.microsoft.com/en-us/library/windows/desktop/ff700543(v=vs.85).aspx
# https://msdn.microsoft.com/en-us/library/windows/desktop/ms632600(v=vs.85).aspx


class GetApplicationName:
    def __init__(self, hWnd, return_full_path=False):
        self.hWnd = hWnd
        self.handle = 0
        self.return_full_path = return_full_path

    def __enter__(self):
        try:
            pid = win32process.GetWindowThreadProcessId(self.hWnd)[1]
            self.handle = win32api.OpenProcess(0x1000, 0, pid)
            full_path = win32process.GetModuleFileNameEx(self.handle, None)
            if self.return_full_path:
                return full_path
            name = os.path.basename(
                full_path)
            if name.endswith('.exe'):
                return name[:-4]
            return name
        except Exception as e:
            return None

    def __exit__(self, *args):
        if self.handle:
            win32api.CloseHandle(self.handle)


class WindowsScreen(BaseScreen):
    def get_windows(self, return_full_path=False):
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
        for hWnd in hWnds:
            if hWnd != self.current_window:
                text = win32gui.GetWindowText(hWnd)
                if text:
                    with GetApplicationName(hWnd, return_full_path=return_full_path) as app:
                        if app:
                            ret.append((app, text, hWnd, hWnd)) # int
        return ret

    def list_windows_as_json(self):
        ret = self.get_windows(return_full_path=True)
        L = []
        for item in ret:
            path = item[0]
            path = path.replace('\\', '/')
            if '/Windows/' in path:
                continue
            name = os.path.basename(path)
            if name.endswith('.exe'):
                name = name[:-4]
            obj = {
                "Keyword": name.lower(),
                "Platform": "Windows",
                "Command": path
            }
            L.append(obj)
        out_s = json.dumps(L, ensure_ascii=False, indent=2)
        print(out_s)
            

    def activate_window(self, hWnd):
        is_previous_disable = win32gui.EnableWindow(hWnd, True)
        # see window style WS_DISABLED
        # A disabled window cannot receive input from the user
        win32com.client.Dispatch('WScript.Shell').SendKeys('^')#%')
        # must send key, someone says it's a pywin32 bug

        style = win32gui.GetWindowLong(hWnd, win32con.GWL_STYLE)
        if style & win32con.WS_MINIMIZE:
            # win32gui.SetWindowLong()'s position is negative
            # win32gui.SetWindowPos() can not get origin position
            if not win32gui.ShowWindow(hWnd, win32con.SW_RESTORE):
                pass
                # subprocess.call(
                #     ['give_me_admin_privilege', str(hWnd), 'restore'],
                #     shell=True,
                # )
        else:
            win32gui.SetForegroundWindow(hWnd)
        if is_previous_disable:
            win32gui.EnableWindow(hWnd, False)

    def close_window(self, hWnd):
        # WM_DESTROY did not work
        # DestroyWindow can only be called by the thread that created the window
        try:
            # win32gui.SendMessage(hWnd, win32con.WM_CLOSE)
            win32gui.PostMessage(hWnd, win32con.WM_CLOSE)
        except Exception as e:
            pid = win32process.GetWindowThreadProcessId(hWnd)[1]
            handle = win32api.OpenProcess(win32con.PROCESS_TERMINATE, 0, pid)
            if handle:
                win32api.TerminateProcess(handle, 0)
                win32api.CloseHandle(handle)
            else:
                self.activate_window(hWnd)

def parse_virtual_key(text):
    if text.startswith('0x'):
        return int(text, base=16)
    elif text.isdigit():
        return int(text)
    elif text.startswith('VK'):
        return eval('win32con.'+text)
    return None


def parse_hotkey_mode(text):
    text = text.lower()
    mod_map = {'alt': win32con.MOD_ALT, 'ctrl':win32con.MOD_CONTROL, 'shift': win32con.MOD_SHIFT}
    return mod_map.get(text)
    

if __name__ == '__main__':

    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        WindowsScreen().list_windows_as_json()
        sys.exit(0)

    kuma = Travel(WindowsScreen())

    byref = ctypes.byref
    user32 = ctypes.windll.user32

    # NOTE: use same shortcut
    lucky_id = 13425
    lucky_key = 0xBA # ;/:
    lucky_mode = win32con.MOD_CONTROL

    if 'hotkey' in kuma.options:
        lucky_key = parse_virtual_key(kuma.options['hotkey']) or lucky_key
    if 'hotkey_mode' in kuma.options:
        lucky_mode = parse_hotkey_mode(kuma.options['hotkey_mode']) or lucky_mode

    def send_hotkey():
        # https://msdn.microsoft.com/en-us/library/dd375731(v=vs.85).aspx
        user32.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        user32.keybd_event(lucky_key, 0, 0, 0)
        user32.keybd_event(lucky_key, 0, win32con.KEYEVENTF_KEYUP, 0)
        user32.keybd_event(
            win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)


    class Listen(QThread):
        _show = pyqtSignal(name='show')

        def run(self):
            # must register in the thread
            # https://msdn.microsoft.com/en-us/library/ms646309.aspx
            # some variable do not exist in win32con, for example VK_OEM_1
            # you can check valid variables using following code:
            # pprint([key for key in dir(win32con) if key.startswith('VK_')])
            if not user32.RegisterHotKey(
                    None, lucky_id, lucky_mode, lucky_key):
                return send_hotkey()
            try:
                msg = wintypes.MSG()
                while user32.GetMessageA(byref(msg), None, 0, 0) != 0:
                    if msg.message == win32con.WM_HOTKEY:
                        self._show.emit()
                    user32.TranslateMessage(byref(msg))
                    user32.DispatchMessageA(byref(msg))
                    if not kuma.running:
                        break
            finally:
                user32.UnregisterHotKey(None, lucky_id)

    main(kuma, Listen())
