import win32gui
import win32com.client
#from pprint import pprint
from base import Data
import re


# Only for windows
# NOTE: pip install win32gui may raise ImportError: No module named win32gui
# Download exe from the following url:
# https://sourceforge.net/projects/pywin32/files/pywin32/


# When you opened many applications, it's hard to move to the application you want,
# the workflow can bring the application to top level whose title or classname match the regular expression you give
# if there are more than one application match, then popup for selection
# if you give nothing that means all applications match


def show_window(hWnd):
    win32com.client.Dispatch('WScript.Shell').SendKeys('%') # it's a pywin32 bug
    win32gui.SetForegroundWindow(hWnd)


class DataToTop(Data):
    def run(self, app, idx):
        show_window(self.data[idx][-1])
        return 'destroy'


def main(param):
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

    param = param.strip()
    if param:
        reg_param = re.compile(param)
        ret = []
        for h, t in ht_pairs:
            c = win32gui.GetClassName(h)
            if reg_param.search(t) or reg_param.search(c):
                ret.append((c, '', t, h))
    else:
        ret = [(win32gui.GetClassName(h), '', t, h) for h, t in ht_pairs]

    if len(ret) == 1:
        show_window(ret[0][-1])
        return 'destroy'
    else:
        return DataToTop(sorted(ret))
