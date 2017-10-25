#from pprint import pprint
from base import Data
import re
import platform

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




# When you opened many applications, it's hard to move to the application you want,
# the workflow can bring the application to top level whose title or classname match the regular expression you give
# if there are more than one application match, then popup for selection
# if you give nothing that means all applications match



class WindowsScreen:
    def get_matched_windows(self, param):
        ht_pairs = []

        def valid(hWnd, param):
            """
            Delete invalid windows,
            following windows I can only remove them by hard:
            'Windows Shell Experience 主机', 'Program Manager', '设置'
            """
            if (win32gui.IsWindow(hWnd)
                and win32gui.IsWindowEnabled(hWnd)
                and win32gui.IsWindowVisible(hWnd)):

                text = win32gui.GetWindowText(hWnd)
                if text and text not in {
                        'Windows Shell Experience 主机',
                        'Program Manager',
                        '设置',
                        'If you were to go on a trip... where would you like to go?'
                }:
                    ht_pairs.append((hWnd, text))

        win32gui.EnumWindows(valid, 0)
        if param:
            ret = []
            for h, t in ht_pairs:
                c = win32gui.GetClassName(h)
                if param.search(t) or param.search(c):
                    ret.append((c, '', t, h))
        else:
            ret = [(win32gui.GetClassName(h), '', t, h) for h, t in ht_pairs]
        return ret

    def show_window(self, hWnd):
        win32com.client.Dispatch('WScript.Shell').SendKeys('%')
        # must send key, someone says it's a pywin32 bug
        win32gui.SetForegroundWindow(hWnd)


class LinuxScreen:
    """I do not use multi-workspace"""
    def get_matched_windows(self, param):
        screen = Wnck.Screen.get_default()
        screen.force_update()
        all_windows = screen.get_windows()

        app_windows = [(w.get_application().get_name(), w) for w in all_windows]

        app_windows = [(app, w) for app, w in app_windows
                       if app not in {'xfce4-panel', 'xfdesktop'}]

        if param:
            ret = []
            for app, w in app_windows:
                name = w.get_name()
                if param.search(app): # or param.search(name):
                    ret.append((app, '', name, w))
        else:
            ret = [(app, '', w.get_name(), w) for app, w in app_windows]
        return ret

    def show_window(self, w):
        """
        0 will got warning, but I can not find a better way:
        (.:15617): Wnck-WARNING **: Received a timestamp of 0; window activation may not function properly.
        """
        w.activate(0)







def main(param):
    param = param.strip()
    if param:
        param = re.compile(param, re.IGNORECASE)

    if PLATFORM == 'Windows':
        obj = WindowsScreen()
    elif PLATFORM == 'Linux':
        obj = LinuxScreen()
    else:
        # Mac need AppKit
        raise NotImplementedError(PLATFORM)

    ret = obj.get_matched_windows(param)

    class DataToTop(Data):
        def run(self, app, idx):
            obj.show_window(self.data[idx][-1])
            return 'destroy'

    if len(ret) == 1:
        obj.show_window(ret[0][-1])
        return 'destroy'
    else:
        return DataToTop(sorted(ret))
