from base import Data, Message
import re
import platform
from abc import abstractmethod


# When you opened many applications, it's hard to activate specific application.
# This workflow can bring the application, whose name (not title) match the regular expression you give, to topmost
# If there are more than one applications match, then popup for selection
# If you give nothing that means popup all applications
# If you give $pattern, then the workflow will kill all the applications whose name is pattern, case insensitive. If nothing, then popup those match the regular expression for kill



PLATFORM = platform.system() # {Linux Windows Darwin}
if PLATFORM == 'Windows':
    import win32gui
    import win32com.client
    # NOTE: pip install win32gui may raise ImportError: No module named win32gui
    # Download exe from the following url:
    # https://sourceforge.net/projects/pywin32/files/pywin32/
elif PLATFORM == 'Linux':
    import gi
    gi.require_version('Wnck', '3.0')
    from gi.repository import Wnck
    # sudo apt-get install python3-gi gir1.2-wnck-3.0
    # my xubuntu 16.04 has already installed them






class BaseScreen:
    def get_matched_windows(self, pattern, kill=False):
        poss = self.get_windows(kill)
        if pattern:
            if kill:
                ret = [row[-1] for row in poss
                       if pattern in {row[0].lower(), row[2].lower()}]
                if ret:
                    return ret
                else:
                    pattern = re.compile(pattern, re.IGNORECASE)
            return [row for row in poss
                    if pattern.search(row[0]) or pattern.search(row[2])]
        else:
            return poss

    @abstractmethod
    def get_windows(self, kill):
        """Return (app_name, '', title, hw) tuple"""
        pass

    @abstractmethod
    def show_window(self, hw):
        pass

    @abstractmethod
    def close_window(self, hw):
        pass


class WindowsScreen(BaseScreen):
    """GetClassName is not good enough, but I have no better idea"""
    def get_windows(self, kill):
        ret = []

        def valid(hWnd, param):
            """
            Filter invalid windows,
            Following windows I can only remove them by hard coding:
            """
            if (win32gui.IsWindow(hWnd)
                and win32gui.IsWindowEnabled(hWnd)
                and win32gui.IsWindowVisible(hWnd)):

                text = win32gui.GetWindowText(hWnd)
                if text not in {'Windows Shell Experience 主机',
                                'Program Manager', '设置', ''}:
                    ret.append((win32gui.GetClassName(hWnd), '', text, hWnd))

        win32gui.EnumWindows(valid, 0)
        self.current_window = win32gui.GetActiveWindow()
        return ret

    def show_window(self, hWnd):
        win32com.client.Dispatch('WScript.Shell').SendKeys('^')#%')
        # must send key, someone says it's a pywin32 bug
        win32gui.SetForegroundWindow(hWnd)

    def close_window(self, hWnd):
        """
        DestroyWindow() can only be called by the thread that created the window
        """
        import win32con
        win32gui.SendMessage(hWnd, win32con.WM_CLOSE) # WM_DESTROY did not work


class LinuxScreen(BaseScreen):
    """I do not use multi-workspace"""

    def get_windows(self, include):
        screen = Wnck.Screen.get_default()
        screen.force_update()
        self.current_window = screen.get_active_window()

        all_windows = screen.get_windows()
        ret = []
        for w in all_windows:
            app = w.get_application().get_name()
            if app not in {'xfce4-panel', 'xfdesktop'}:
                ret.append((app, '', w.get_name(), w))
        return ret

    def show_window(self, hw):
        """Got warning, but I can not find a better way"""
        hw.activate(0)

    def close_window(self, hw):
        hw.close(0)







def main(pattern):
    pattern = pattern.strip()
    kill = False
    if pattern.startswith('$'):
        kill = True
        pattern = pattern[1:].lower()
        if not pattern:
            return Message('No matched application to kill')
    elif pattern:
        pattern = re.compile(pattern, re.IGNORECASE)

    if PLATFORM == 'Windows':
        obj = WindowsScreen()
    elif PLATFORM == 'Linux':
        obj = LinuxScreen()
    else:
        # Mac need AppKit
        raise NotImplementedError(PLATFORM)


    class DataToKill(Data):
        def run(self, app, idx):
            obj.show_window(self.data[idx][-1])
            obj.close_window(self.data[idx][-1])
            if len(self.data) == 1:
                return 'destroy'
            obj.show_window(obj.current_window)
            self.data = self.data[:idx] + self.data[idx+1:]
            return self


    class DataToTop(Data):
        def run(self, app, idx):
            obj.show_window(self.data[idx][-1])
            return 'destroy'


    ret = obj.get_matched_windows(pattern, kill)
    if kill:
        if not ret:
            return Message('No matched application to kill')
        if hasattr(ret[0], '__len__'):
            return DataToKill(sorted(ret))
        else:
            for hw in ret:
                obj.show_window(hw) # some application will pop up a quit dialog
                obj.close_window(hw)
            return 'destroy'

    if len(ret) == 1:
        obj.show_window(ret[0][-1])
        return 'destroy'
    else:
        return DataToTop(sorted(ret))
