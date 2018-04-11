import time
import os
import platform
from functools import wraps, partial
# from collections import deque
import tkinter as tk
import bisect
import re
import webbrowser
import subprocess
from abc import abstractmethod
from base import Data, Message



# FIXME: if I set the frame's maxwidth != minwidth, then when the completion (say a filename) is too long, after typing enter on it, we will see cursor not in the sight of input entry, because width is shorten and it seems happens after my callback function finished (I use adjust_xview after quit popup, did not work)


# TODO: more smooth continuous movement (a char)? (when call by script improved a bit)

# TODO: I didn't have a mac, so I can not test all the mac thing, may do those on a virtual machine

# TODO: kill ring?
# TODO: history and match, not allow repeat?
# TODO: add logging?
# TODO: add app icon?
# TODO: use scrollbar, bottom page index or top scrollbar-like thing?



# NOTE: emacs's mark is too complicated, so I simplified it:
# every kill (decorated by), undo will delete mark

# I'm not sure: pack or pack_forget multiple times influence speed
# I use array to indicate same kind of widget's visibility, did not record if only one



########################################################################
# global variables
########################################################################
try:
    path = os.path.split(os.path.realpath(__file__))[0]
except NameError:
    path = os.getcwd() or os.getenv('PWD')


PLATFORM = platform.system() # {Linux Windows Darwin}
open_command = {'Linux': 'xdg-open',
                'Windows': {True: 'start', False: 'call'}, # open a dir or not
                'Darwin': 'open'}
assert PLATFORM in open_command



########################################################################
# color and font
########################################################################
input_bg = '#bebebe'
desc_fg = '#696969' # description

bg = '#d3d3d3'
fg = '#000000'

hl_bg = '#4682b4'
hl_fg = '#ffffff'


# font_main = ('monaco', 20)
# font_desc = ('monaco', 14)

font_main = ('YouYuan', 28)
font_desc = ('YouYuan', 20)




########################################################################
# useful functions
########################################################################
def print_event():
    """
    Strike keyboard to print corresponding event
    NOTE: ] is not keysym, bracketright is
    NOTE: Alt + 1-5 does not work, use <Alt-KeyPress-1> instead:
    https://mail.python.org/pipermail/tkinter-discuss/2013-September/003488.html
    """
    fred = tk.Entry()
    fred.pack()
    fred.focus_set()
    fred.bind('<KeyPress>', lambda event: print(event.__dict__))
    fred.mainloop()


def get_char_type(c):
    """Add your language's word's characters"""
    if 'a' <= c <= 'z' or 'A' <= c <= 'Z' or '0' <= c <= '9':
        return 'english'
    if 0x4e00 <= ord(c) <= 0x9fa6:
        return 'chinese'
    return None


def is_inserting(event):
    """
    Check if the event is inserting a character

    |   Mask | Modifier        |
    |--------+-----------------|
    | 0x0001 | Shift.          |
    | 0x0002 | Caps Lock.      |
    | 0x0004 | Control.        |
    | 0x0008 | Left-hand Alt.  |
    | 0x0010 | Num Lock.       |
    | 0x0080 | Right-hand Alt. |
    | 0x0100 | Mouse button 1. |
    | 0x0200 | Mouse button 2. |
    | 0x0400 | Mouse button 3. |
    See http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/event-handlers.html

    without modifier, state = 0, then add all modifier.
    but I found Num Lock is 0x0008 in windows
    TODO: find a document or post which declare it, test on Mac
    """
    if event.char != '':
        # Windows: NumLock, ScrLk, NumLock+ScrLk
        # Linux: NumLock
        poss = (0, 8, 32, 40) if PLATFORM == 'Windows' else (0, 16)
        for p in poss:
            if event.state < p:
                break
            elif event.state < p + 4: # Shift, Caps Lock
                return True
    return False



class DataComplete(Data):
    def __init__(self, data, _from=0):
        super().__init__(data)
        self._from = _from

    def run(self, app, idx):
        app.insert_one_greedy(self.data[idx][0], self._from)
        app.save_state_if_needed()



class Row(tk.Frame):
    """
    About icon display:
    http://effbot.org/pyfaq/why-do-my-tkinter-images-not-appear.htm
    """
    def __init__(self, master, index):
        super().__init__(master, bg=bg)
        self.pack(fill='x')
        self.master = master
        self.index = index

        self.left = tk.Label(self, anchor='w', font=font_main, bg=bg)
        self.left.pack(fill='y', side='left')
        self.right = tk.Label(self, anchor='w', font=font_main, bg=bg)
        self.right.pack(fill='x')
        self.down = tk.Label(self, anchor='w', font=font_desc, bg=bg, fg=desc_fg)
        # self.down.pack(fill='x')
        self.down_packed = False

    def highlight(self):
        self.left['bg'] = self.right['bg'] = self.down['bg'] = hl_bg
        self.left['fg'] = self.right['fg'] = self.down['fg'] = hl_fg

    def unhighlight(self):
        self.left['bg'] = self.right['bg'] = self.down['bg'] = bg
        self.left['fg'] = self.right['fg'] = fg
        self.down['fg'] = desc_fg

    def update_data(self, data, type_width):
        n = len(data)
        assert n > 0
        self.right['text'] = data[0]
        self.left['text'] = data[1] if n > 1 else ''
        self.left['width'] = type_width + 1 if type_width else 0
        if n < 3 or not data[2]:
            # self.down['text'] = ''
            if self.down_packed:
                self.down_packed = False
                self.down.pack_forget()
        else:
            self.down['text'] = data[2]
            if not self.down_packed:
                self.down_packed = True
                self.down.pack(fill='x')



def movebd(func):
    """Move between data"""
    @wraps(func)
    def wrapper(self, *args):
        if self.total:
            pre_ipage, pre_hl_idx = self.ipage, self.hl_idx
            func(self, *args)
            if pre_ipage != self.ipage:
                self.update_display()
            if pre_hl_idx != self.hl_idx:
                self.highlight(pre_hl_idx)
        return 'break'
    return wrapper


class Popup(tk.Frame):
    def __init__(self, master):
        """
        relief: {flat, groove, raised, sunken, ridge}
        removed bottom page index with multi-pages
        """
        super().__init__(master, borderwidth=2, relief='ridge', bg=bg)
        self.master = master
        self.maxdisp = 9 # for golden row

        self.rows = []

        self.data = None
        self.ipage = 0
        self.page_1 = 0 # total page - 1
        self.total = 0
        self.hl_idx = 0
        self.packed = [False] * self.maxdisp

    def update_display(self):
        start = self.ipage * self.maxdisp
        hl_max = self.total - start

        type_width = max(len(self.data[start + i][1])
                         for i in range(min(hl_max, self.maxdisp)))
        for i, row in enumerate(self.rows):
            if i < hl_max:
                if not self.packed[i]:
                    row.pack(fill='x')
                    self.packed[i] = True
                row.update_data(self.data[start + i], type_width)
            else:
                row.pack_forget()
                self.packed[i] = False

    def update_data(self, data):
        """Guarantee sorted"""
        if not self.rows:
            self.rows = [Row(self, i) for i in range(self.maxdisp)]
            self.rows[0].highlight()
        pre_hl_idx = self.hl_idx
        self.data = data
        self.total = len(data)
        self.page_1 = (self.total - 1) // self.maxdisp
        self.pack(fill='x', pady=(2, 0))
        self.ipage = max(0, min(data.init_ipage, self.page_1))
        self.hl_idx = min(data.init_index, self.maxdisp - 1)
        self.guarantee_not_exceed()
        self.update_display()
        self.highlight(pre_hl_idx)

    def quit(self):
        self.total = 0
        self.pack_forget()

    def highlight(self, pre_hl_idx):
        self.rows[pre_hl_idx].unhighlight()
        self.rows[self.hl_idx].highlight()

    def run(self):
        if self.total:
            return self.data.run(
                self.master, self.ipage * self.maxdisp + self.hl_idx)

    def guarantee_not_exceed(self):
        temp = self.total - 1 - self.ipage * self.maxdisp
        if self.hl_idx > temp:
            self.hl_idx = temp

    @movebd
    def next_page(self, event):
        if self.ipage < self.page_1:
            self.ipage += 1
            self.guarantee_not_exceed()

    @movebd
    def previous_page(self, event):
        if self.ipage > 0:
            self.ipage -= 1

    @movebd
    def beginning_of_data(self, event):
        self.ipage = 0
        self.hl_idx = 0

    @movebd
    def end_of_data(self, event):
        if self.ipage < self.page_1:
            self.ipage = self.page_1
            self.hl_idx = self.total - 1 - self.ipage * self.maxdisp

    @movebd
    def next_row(self, event):
        if self.hl_idx < self.maxdisp - 1 and self.packed[self.hl_idx + 1]:
            self.hl_idx += 1

    @movebd
    def previous_row(self, event):
        if self.hl_idx > 0:
            self.hl_idx -= 1

    @movebd
    def move_to_golden_row(self, event):
        """Designed for fewest keystrokes"""
        n = sum(self.packed)
        if n > 7:
            m = 2
        elif n > 4:
            m = 1
        else:
            m = 0
        self.hl_idx = n - 1 - m if self.hl_idx < (n >> 1) else m

    @movebd
    def cycle_page(self, event):
        if self.ipage < self.page_1:
            self.ipage += 1
            self.guarantee_not_exceed()
        else:
            self.ipage = 0

    @movebd
    def cycle_page_reverse(self, event):
        if self.ipage > 0:
            self.ipage -= 1
        else:
            self.ipage = self.page_1
            self.guarantee_not_exceed()



def create_root():
    root = tk.Tk()
    root.title('kuma')
    # If you were to go on a trip... where would you like to go?
    width, height = root.maxsize()
    width_min = width * 5 // 12
    # root.maxsize(width_min, height)
    root.maxsize(width // 2, height)
    root.minsize(width_min, 1)
    root.resizable(0, 0)
    root.geometry('+{}+{}'.format((width - width_min) // 2, height // 4))
    return root


def move(func):
    @wraps(func)
    def wrapper(self, *args):
        func(self, *args)
        if self.selected:
            self.select()
        if self.popup.total:
            self.popup.quit()
        self.adjust_xview()
        self.previous = 'move'
        return 'break'
    return wrapper


def kill(func):
    @wraps(func)
    def wrapper(self, *args):
        self.save_state_if_needed()
        func(self, *args)
        self.save_state_if_needed()
        if self.selected:
            self.unselect()
        if self.popup.total:
            self.popup.quit()
        self.adjust_xview()
        self.mark = None
        self.previous = 'delete' if func.__name__.endswith('_char') else 'kill'
        return 'break'
    return wrapper


def save_unselect_and_quit(func):
    @wraps(func)
    def wrapper(self, *args):
        self.save_state_if_needed()
        func(self, *args)
        self.save_state_if_needed()
        if self.selected:
            self.unselect()
        if self.popup.total:
            self.popup.quit()
        self.adjust_xview()
        self.previous = func.__name__
        return 'break'
    return wrapper


class Travel(tk.Frame):
    def __init__(self, screen, is_hidden=False,
                 keyword_file='config.org'):
        self.screen = screen
        self.master = create_root()
        super().__init__(self.master)
        self.pack(fill='x')

        self.keyword_file = os.path.join(path, keyword_file)
        # use modification time to determine to reload or not
        self.keyword_mtime = 0

        self.states = ['']
        self.positions = [0]
        self.idx = 0

        # self.kill_ring = deque() # TODO: emacs-like kill ring

        self.previous = None

        self.mark = None
        self.selected = False
        # selection_present() can not present one point selection
        # so we must do it by hand
        # Only three ways will turn self.selected to True:
        # 1. self.select_all
        # 2. self.set_mark
        # 3. self.exchange_point_and_mark

        self._topmost = False


        self.input = tk.Entry(self, borderwidth=1, bg=input_bg,
                              font=font_main, selectbackground=hl_bg,
                              selectforeground=hl_fg,
                              insertwidth=2, exportselection=0)
        self.input.pack(fill='x', padx=(1, 0))
        self.input.focus_set()

        self.popup = Popup(self)


        self.win_drives = None
        self.win_drive_template = '{}:/' # + os.path.sep


        self.is_hidden = is_hidden
        if self.is_hidden:
            self.master.withdraw()
        else:
            self._show()

        # NOTE: now you can not kill kuma by closing window
        # Linux's send_event discouraged me deeply,
        # This is the only way I can think out
        self.master.protocol('WM_DELETE_WINDOW', self._destroy)


        # keybinding
        self.input.bind('<Return>', self.run)
        self.input.bind('<Tab>', self.complete)
        self.input.bind('<Control-g>', self.keyboard_quit)
        self.input.bind('<Escape>', self.quit)


        self.input.bind('<Control-f>', self.forward_char)
        self.input.bind('<Control-b>', self.backward_char)
        self.input.bind('<Alt-f>', self.forward_word)
        self.input.bind('<Alt-b>', self.backward_word)
        self.input.bind('<Control-a>', self.move_beginning_of_line)
        self.input.bind('<Control-e>', self.move_end_of_line)
        self.input.bind('<Control-d>', self.delete_char)
        self.input.bind('<BackSpace>', self.backward_delete_char)
        self.input.bind('<Alt-d>', self.kill_word)
        self.input.bind('<Alt-BackSpace>', self.backward_kill_word)
        self.input.bind('<Control-k>', self.kill_line)
        # self.input.bind('<>', self.backward_kill_line)
        self.input.bind('<Control-space>', self.set_mark)
        self.input.bind('<Control-at>', self.set_mark)
        self.input.bind('<Control-x>', self.exchange_point_and_mark) #
        self.input.bind('<Alt-h>', self.select_all)
        self.input.bind('<Alt-w>', self.copy)
        self.input.bind('<Control-w>', self.cut)
        self.input.bind('<Control-y>', self.paste)
        self.input.bind('<Control-slash>', self.undo)

        self.input.bind('<KeyPress>', self.key_press)
        self.input.bind('<Control-t>', self.transpose_chars)
        self.input.bind('<Alt-t>', self.toggle_topmost)


        self.input.bind('<Alt-bracketright>', self.popup.next_page)
        self.input.bind('<Alt-bracketleft>', self.popup.previous_page)
        self.input.bind('<Control-n>', self.popup.next_row)
        self.input.bind('<Control-p>', self.popup.previous_row)
        self.input.bind('<Alt-Shift-greater>', self.popup.end_of_data)
        self.input.bind('<Alt-Shift-less>', self.popup.beginning_of_data)
        self.input.bind('<Control-l>', self.popup.move_to_golden_row)

        if PLATFORM == 'Linux':
            self.input.bind('<ISO_Left_Tab>', self.popup.cycle_page_reverse)
        else:
            self.input.bind('<Shift-KeyPress-Tab>',
                            self.popup.cycle_page_reverse)


        # # NOTE: change following to window motion
        # self.input.bind('<Right>', self.popup.next_page)
        # self.input.bind('<Left>', self.popup.previous_page)
        # self.input.bind('<Down>', self.popup.next_row)
        # self.input.bind('<Up>', self.popup.previous_row)

        self.input.bind('<Right>', partial(self.reset_window_position, dx=24))
        self.input.bind('<Left>', partial(self.reset_window_position, dx=-24))
        self.input.bind('<Down>', partial(self.reset_window_position, dy=24))
        self.input.bind('<Up>', partial(self.reset_window_position, dy=-24))

        # unbind default keybindings
        for e in self.input.event_info():
            self.input.event_delete(e) # event_add to add

        # disable mouse click
        self.input.bind('<Button-1>', self.dummy)
        self.input.bind('<Button-2>', self.dummy)
        self.input.bind('<Button-3>', self.dummy)
        self.input.bind('<B1-Motion>', self.dummy)
        self.input.bind('<B2-Motion>', self.dummy)
        self.input.bind('<B3-Motion>', self.dummy)

    def reset_window_position(self, event, dx=0, dy=0):
        _, x, y = self.master.wm_geometry().split('+')
        self.master.wm_geometry('+{}+{}'.format(int(x) + dx, int(y) + dy))

    @property
    def pos_cur(self):
        return self.input.index('insert')

    @property
    def pos_end(self):
        return self.input.index('end')

    def select(self):
        if self.mark is not None:
            self.input.selection_range(*sorted((self.mark, self.pos_cur)))

    def unselect(self):
        self.selected = False
        self.input.selection_clear()

    def save_state_if_needed(self):
        """Since move operation won't be saved, the position is interesting"""
        temp = self.input.get()
        if self.states[-1] != temp:
            self.states.append(temp)
            self.positions.append(self.pos_cur)
        else:
            self.positions[-1] = self.pos_cur

    def clipboard_append(self, content):
        if self.previous != 'kill':
            self.input.clipboard_clear()
        self.input.clipboard_append(content)

    def clipboard_append_left(self, content):
        if self.previous == 'kill':
            content += self.input.clipboard_get()
        self.input.clipboard_clear()
        self.input.clipboard_append(content)



    def dummy(self, event):
        return 'break'

    def keyboard_quit(self, event):
        if self.popup.total:
            self.popup.quit()
        elif self.selected:
            self.unselect()
        return 'break'

    def quit(self, event):
        if self.popup.total:
            self.popup.quit()
        else:
            self._destroy()
        return 'break'

    def show_message(self, msg):
        m = tk.Message(
            self, aspect=6000, text=msg.text, anchor='w',
            font=font_main, relief='ridge', borderwidth=2)
        m.pack(fill='x', pady=(2, 0))
        m.after(msg.ms, m.destroy)

    def get_win_drives(self):
        """Get possible drive, for windows"""
        if self.win_drives is None:
            self.win_drives = []
            for c in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
                temp = self.win_drive_template.format(c)
                if os.path.isdir(temp):
                    self.win_drives.append((temp, 'D'))

    def complete(self, event):
        """Only two types of completions: path and keywords"""
        if self.selected:
            self.unselect()

        pos_cur = self.pos_cur
        content = self.input.get()
        pre = content[:pos_cur]

        previous, self.previous = self.previous, 'tab'
        self.save_state_if_needed()

        if self.popup.total:
            if previous in {'tab', 'run'}:
                self.popup.cycle_page(event)
            elif previous == 'insert':
                if self.popup.total == 1:
                    self.insert_one_greedy(
                        self.popup.data[0][0], self.popup.data._from)
                else:
                    _from = self.popup.data._from
                    prefix = self.longest_common_prefix(self.popup.data, _from)
                    if len(prefix) > _from:
                        self.input.insert('insert', prefix[_from:])
                        self.adjust_xview()
                        self.popup.data._from = len(prefix)
                    # should move to first?
            return 'break'

        if pre == '~':
            self.input.insert(pos_cur, '/')
            return 'break'

        if pre.startswith('/') or pre.startswith('~/'):
            # os.path.split (os.path.dirname, os.path.basename)
            # os.path.expanduser os.path.join os.sep os.pathsep
            if PLATFORM == 'Windows' and pre[0] == '/':
                lpre = len(pre) - 1
                if lpre < 3:
                    if lpre > 0:
                        temp = self.win_drive_template.format(pre[1])
                        if os.path.isdir(temp):
                            self.insert_one_greedy(temp, lpre)
                            # self.input.insert(pos_cur, temp[lpre:])
                    else:
                        self.get_win_drives()
                        if len(self.win_drives) == 1:
                            self.insert_one_greedy(self.win_drives[0], 0)
                            # self.input.insert(pos_cur, self.win_drives[0])
                        else:
                            self.popup.update_data(self.win_drives)
                    return 'break'
                pre = pre[1:]

            dirname, basename = os.path.split(os.path.expanduser(pre))
            result = []
            for root, dirs, files in os.walk(dirname):
                if root != dirname:
                    break
                result.extend(sorted((d + '/', 'D') for d in dirs
                                     if d.startswith(basename)))
                # os.path.sep -> '/', ord('/') = 47 while ord('\\') = 92
                result.extend(sorted((f, '') for f in files
                                     if f.startswith(basename)))
            self._complete(result, basename)
        else:
            self.load_keywords()
            if pre == '':
                result = self.kv_list_sorted_by_type
            else:
                i = bisect.bisect_left(self.keywords, pre)
                result = []
                while i < self.nkeyword:
                    if not self.keywords[i].startswith(pre):
                        break
                    result.append(self.kv_list[i])
                    i += 1
                result.sort(key=lambda x: x[1]) # stable sort

            self._complete(result, pre)
        return 'break'

    def _complete(self, result, pre):
        n = len(result)
        start = len(pre)
        if n > 1:
            prefix = self.longest_common_prefix(result, start)
            if len(prefix) > start:
                self.input.insert('insert', prefix[start:])
                self.adjust_xview()
            self.popup.update_data(DataComplete(result, len(prefix)))
        elif n == 1:
            self.insert_one_greedy(result[0][0], start)
        else:
            self.popup.quit()

    def longest_common_prefix(self, result, start):
        n = len(result)
        min_idx, max_idx = 0, n - 1
        for i in range(1, n): # n not n - 1
            if result[i][1] != result[i - 1][1]:
                if result[i - 1][0] > result[max_idx][0]:
                    max_idx = i - 1
                if result[i][0] < result[min_idx][0]:
                    min_idx = i
        min_res, max_res = result[min_idx][0], result[max_idx][0]
        n = min(len(min_res), len(max_res))
        for i in range(start, n):
            if min_res[i] < max_res[i]:
                return min_res[:i]
        return min_res[:n]

    def insert_one_greedy(self, data, start):
        """
        Greedy tail match completion and inserting

        for example:
        ~/packages/em(cursor here, then Tab).org
        should to ~/packages/emacs.org, rather than ~/packages/emacs.org.org

        ba(cursor here, then Tab)u hello -> baidu (cursor here)hello
        """
        content = self.input.get()
        pos_cur = self.pos_cur
        data = data[start:]

        # space will not occur in keyword
        # a directory or file can endswith space

        # two case [non-greedy, greedy] should insert or not
        insert_blank = [content[pos_cur:pos_cur+1] != ' ', True]
        tail = content[pos_cur:]
        is_keyword = True
        if content.startswith('~/') or content.startswith('/'):
            is_keyword = False
            for i, c in enumerate(tail):
                if c == '/' or (PLATFORM == 'Windows' and c == '\\'):
                    tail = tail[:i] + '/'
                    break
        else:
            for i, c in enumerate(tail):
                if c == ' ':
                    insert_blank[1] = False
                    tail = tail[:i]
                    break

        self.popup.quit()
        if tail and data.endswith(tail):
            self.input.insert(pos_cur, data[:-len(tail)])
            self.input.icursor(pos_cur + len(data))
            insert_blank = insert_blank[1]
        else:
            self.input.insert(pos_cur, data)
            insert_blank = insert_blank[0]

        if is_keyword:
            if insert_blank:
                self.input.insert('insert', ' ')
            else:
                self.input.icursor(pos_cur + len(data) + 1)
        self.adjust_xview()

    def key_press(self, event):
        """NOTE: character won't be inserted unless the function is finished"""
        if is_inserting(event):
            if self.selected:
                self.unselect()
            self.previous = 'insert'
            if self.popup.total:
                if isinstance(self.popup.data, DataComplete):
                    result = []
                    _from = self.popup.data._from
                    for row in self.popup.data:
                        if row[0][_from:_from+1] == event.char:
                            result.append(row)
                    if not result:
                        self.popup.quit()
                    elif len(result) == len(self.popup.data):
                        self.popup.data._from += 1
                    else:
                        self.popup.update_data(DataComplete(result, _from + 1))
                else:
                    self.popup.quit()

    def run(self, event):
        ret = self._run(event)
        self.previous = 'run'
        if ret == 'hold':
            pass
        elif ret == 'destroy':
            self._destroy()
        elif isinstance(ret, Data) and len(ret):
            self.popup.update_data(ret)
        elif isinstance(ret, Message):
            self.show_message(ret)
        else:
            self.popup.quit()
        return 'break'

    def _run(self, event):
        if self.popup.total:
            return self.popup.run()

        cmd = self.input.get().rstrip(' ')
        if not cmd:
            return self.screen.activate('') # 'hold'

        is_a_path = cmd[0] == '/'
        if PLATFORM == 'Windows' and cmd[0] == '/':
            cmd = cmd[1:]
        if cmd.startswith('~/'):
            is_a_path = True
            cmd = os.path.expanduser(cmd)
        if os.path.isdir(cmd) or os.path.isfile(cmd):
            func = open_command[PLATFORM]
            if PLATFORM == 'Windows':
                # It's strange that only shell True is right
                return self._subprocess_popen(
                    [func[os.path.isdir(cmd)], cmd], shell=True)
            else:
                return self._subprocess_popen([func, cmd], shell=False)

        if is_a_path:
            return Message('Invalid path!')

        keyword, *params = cmd.split(' ', maxsplit=1)
        self.load_keywords()
        if keyword not in self.kv_dict:
            pre = cmd
            i = bisect.bisect_left(self.keywords, pre)
            result = []
            while i < self.nkeyword:
                if not self.keywords[i].startswith(pre):
                    break
                result.append(self.kv_list[i])
                i += 1
            if not result:
                return self.screen.activate(cmd)
                # return Message('Unknown keyword: {}!'.format(keyword))
            result.sort(key=lambda x: x[1]) # stable sort
            self.input.delete(0, self.pos_end)
            self.input.insert(0, pre)
            self._complete(result, pre)
            return 'hold'
        else:
            params = params[0].strip() if params else ''
            typ, reg, val = self.kv_dict[keyword]
            typ.capitalize()
            if typ == '~':
                if keyword == 'activate':
                    return self.screen.activate(params)
                elif keyword == 'close':
                    return self.screen.close(params)
                else:
                    return Message(
                        'Unimplemented built-in keyword: {}!'.format(keyword))
            elif typ == 'Web':
                webbrowser.open_new_tab(val.format(params))
                return 'destroy'
                # # NOTE: choose following ways you like
                # webbrowser.open('http://www.python.org')
                # webbrowser.open_new('http://www.python.org')
                # webbrowser.open_new_tab('http://www.python.org')
                # c = webbrowser.get('firefox')
                # c.open('http://www.python.org')
                # c.open_new_tab('http://docs.python.org')
            elif typ == 'App':
                if (params[:5].lower() == 'close'
                    or params[:4].lower() == 'kill'):
                    for pattern in [reg, keyword]:
                        if pattern:
                            ret = self.screen.close(pattern)
                            if not isinstance(ret, Message):
                                return ret
                    return ret
                elif params[:3].lower() == 'new':
                    return self._subprocess_popen(
                        '{} {}'.format(val, params[3:]), shell=True)

                for pattern in [reg, cmd]:
                    if pattern:
                        ret = self.screen.activate(pattern)
                        if not isinstance(ret, Message):
                            return ret
                return self._subprocess_popen(
                    '{} {}'.format(val, params), shell=True)
            elif typ == 'Py':
                dct = {}
                try:
                    exec('from workflow_{} import main'.format(keyword), dct)
                except Exception as e:
                    return Message(repr(e))
                return dct['main'](params)
            else:
                return Message('Unknown type: {}!'.format(typ))

    def _subprocess_popen(self, cmd, shell):
        p = subprocess.Popen(cmd, shell=shell, start_new_session=True,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, universal_newlines=True)
        try:
            _, err = p.communicate(timeout=0.1) # 0.1s
        except subprocess.TimeoutExpired:
            err = ''

        if PLATFORM == 'Linux':
            subprocess.call(['kill', str(p.pid)]) # kill sh -c ... process

        if err:
            return Message(err.strip())
        else:
            return 'destroy'

    @move
    def forward_char(self, event):
        self.input.icursor(min(self.pos_end, self.pos_cur + 1))

    @move
    def backward_char(self, event):
        self.input.icursor(max(0, self.pos_cur - 1))

    def get_previous_word_position(self):
        pos = self.pos_cur - 1
        content = self.input.get()
        pre = None
        while pos >= 0:
            typ = get_char_type(content[pos])
            if pre is None:
                if typ is not None:
                    pre = typ
            else:
                if typ != pre:
                    return pos + 1
            pos -= 1
        return 0

    def get_next_word_position(self):
        pos = self.pos_cur
        content = self.input.get()
        pre = None
        n = len(content)
        while pos < n:
            typ = get_char_type(content[pos])
            if pre is None:
                if typ is not None:
                    pre = typ
            else:
                if typ != pre:
                    return pos
            pos += 1
        return n

    @move
    def forward_word(self, event):
        pos = self.get_next_word_position()
        self.input.icursor(pos)

    @move
    def backward_word(self, event):
        pos = self.get_previous_word_position()
        self.input.icursor(pos)

    @move
    def move_beginning_of_line(self, event):
        self.input.icursor(0)

    @move
    def move_end_of_line(self, event):
        self.input.icursor(self.pos_end)


    @kill
    def delete_char(self, event):
        self.input.delete(self.pos_cur)#, self.pos_cur + 1)

    @kill
    def backward_delete_char(self, event):
        self.input.delete(self.pos_cur - 1)#, self.pos_cur)

    @kill
    def kill_word(self, event):
        pos_cur = self.pos_cur
        pos = self.get_next_word_position()
        content = self.input.get()[pos_cur:pos]
        self.input.delete(pos_cur, pos)
        self.clipboard_append(content)

    @kill
    def backward_kill_word(self, event):
        """M-DEL"""
        pos_cur = self.pos_cur
        pos = self.get_previous_word_position()
        content = self.input.get()[pos:pos_cur]
        self.input.delete(pos, pos_cur)
        self.clipboard_append_left(content)

    @kill
    def kill_line(self, event):
        content = self.input.get()[self.pos_cur:]
        self.input.delete(self.pos_cur, self.pos_end)
        self.clipboard_append(content)

    @kill
    def backward_kill_line(self, event):
        """Emacs no such function"""
        content = self.input.get()[:self.pos_cur]
        self.input.delete(self.pos_cur, self.pos_end)
        self.clipboard_append_left(content)

    def set_mark(self, event):
        """Break continuous undo and kill"""
        self.mark = self.pos_cur
        self.selected = True
        self.input.selection_clear()
        self.previous = 'set_mark'
        return 'break'

    def exchange_point_and_mark(self, event):
        """Only break continuous kill, not undo"""
        if self.mark is not None:
            pos_cur = self.pos_cur
            self.selected = True
            if self.mark != pos_cur:
                self.input.icursor(self.mark)
                self.mark = pos_cur
                self.select()
                if self.previous == 'kill':
                    self.previous = 'exchange'
        return 'break'

    def select_all(self, event):
        self.mark = self.pos_end
        self.input.icursor(0)
        self.selected = True
        self.input.selection_range(0, self.mark)
        self.previous = 'select_all'
        return 'break'

    # mark word? (maybe something like M-h)

    @save_unselect_and_quit
    def transpose_chars(self, event):
        pos_cur = self.pos_cur
        if pos_cur != 0:
            pos_end = self.pos_end
            content = self.input.get()
            if pos_cur == pos_end:
                if pos_cur == 1:
                    self.input.icursor(0)
                else:
                    self.input.delete(pos_cur - 2, pos_cur)
                    self.input.insert('insert', content[-2:][::-1])
            else:
                self.input.delete(pos_cur - 1, pos_cur + 1)
                self.input.insert('insert', content[pos_cur-1:pos_cur+1][::-1])
        return 'break'

    @save_unselect_and_quit
    def copy(self, event):
        """
        NOTE: emacs's implemention is too hard (when highlight is invisible,
        run self.copy, you will see cursor appear on the mark few second,
        but the cursor's actual position is not changed and you can
        interrupt this by using any command)

        extreme case: copy two times
        so self.copy is not in continuous kill

        NOTE: I tryed to implement a splash highlight (use time.sleep(0.1)),
        but it seems redrawing only happens when a function is finished
        """
        if self.mark is not None:
            pos_cur = self.pos_cur
            if pos_cur > self.mark:
                content = self.input.get()[self.mark:pos_cur]
            elif pos_cur < self.mark:
                content = self.input.get()[pos_cur:self.mark]
            else:
                return
            self.input.clipboard_clear()
            self.input.clipboard_append(content)

    def cut(self, event):
        """Same with self.copy, not in continuous kill"""
        if self.mark is not None:
            self.copy(event)
            self.input.delete(*sorted((self.mark, self.pos_cur)))

    @save_unselect_and_quit
    def paste(self, event):
        self.mark = self.pos_cur
        self.input.insert(self.mark, self.input.clipboard_get())

    def undo(self, event):
        if self.previous != 'undo':
            self.idx = len(self.states) - 1
            self.save_state_if_needed()
            if self.selected:
                self.unselect()

        if self.idx > 0:
            self.idx -= 1

            # if self.states[-1] != self.states[self.idx]: # seems useless
            self.states.append(self.states[self.idx])
            self.positions.append(self.positions[self.idx])
            self.input.delete(0, self.pos_end)
            self.input.insert(0, self.states[-1])
            self.input.icursor(self.positions[-1])

            self.mark = None
            self.previous = 'undo'
        return 'break'

    def adjust_xview(self):
        start, end = map(lambda x: int(x * self.pos_end), self.input.xview())
        pos_cur = self.pos_cur
        if pos_cur < start or pos_cur > end:
            self.input.xview('insert')

    def load_keywords(self):
        """
        Lazy load

        I use emacs's org-mode table to organize keywords and values,
        (keyword, type, ..., real command)
        """
        mt = os.path.getmtime(self.keyword_file)
        if self.keyword_mtime != mt:
            self.keyword_mtime = mt
            self.kv_list = []
            self.kv_dict = {}
            with open(self.keyword_file, encoding='utf-8') as f:
                f.readline() # exclude title (the first line)
                for line in f:
                    temp = line.split('|')[1:-1]
                    if len(temp) > 1:
                        temp = [w.strip() for w in temp]
                        if temp[-2] == '' or PLATFORM in temp[-2]:
                            self.kv_list.append(temp[:3])
                            self.kv_dict[temp[0]] = temp[1::2]
            self.kv_list.sort()
            self.kv_list_sorted_by_type = sorted(
                self.kv_list, key=lambda x: x[1])
            self.keywords = [kv[0] for kv in self.kv_list]
            self.nkeyword = len(self.keywords)

    def _destroy(self):
        if not self.is_hidden:
            self.is_hidden = True

            self.states = ['']
            self.positions = [0]
            self.idx = 0

            # self.kill_ring.clear()

            self.previous = None

            self.mark = None
            self.unselect()

            self.input.delete(0, self.pos_end)

            self.popup.quit()

            self.master.withdraw()

    def _show(self):
        root = self.master
        if (not self.is_hidden) and PLATFORM == 'Linux':
            # Linux will not lift to topmost sometimes
            # I can only find withdraw first way to solve it
            # withdraw after withdraw may influence the initial position
            root.withdraw()
        root.update()
        root.deiconify()

        # following is not enough in linux
        root.lift()
        root.attributes('-topmost', True)
        root.attributes('-topmost', False)
        self._topmost = False

        self.input.focus_set()
        self.is_hidden = False

    def toggle_topmost(self, event):
        self._topmost ^= True
        self.master.attributes('-topmost', self._topmost)



class BaseScreen:
    def get_matched_windows(self, pattern):
        self.exact_match = False
        poss = self.get_windows()
        if pattern:
            ret = [win for win in poss
                   if pattern in {win[0].lower(), win[2].lower()}]
            if ret:
                self.exact_match = True
                return ret

            pattern = re.compile(pattern, re.IGNORECASE)
            ret = [win for win in poss if pattern.search(win[0])]
            if ret:
                return ret
            return [win for win in poss if pattern.search(win[2])]
        else:
            return poss

    @abstractmethod
    def get_windows(self):
        """Return list of (app_name, pid, title, hw) tuple
        NOTE: important! RECORD current window
        """
        pass

    @abstractmethod
    def activate_window(self, hw):
        pass

    @abstractmethod
    def close_window(self, hw):
        pass

    def activate_window_safely(self, hw):
        try:
            self.activate_window(hw)
        except Exception as e:
            pass

    def close_window_safely(self, hw):
        try:
            self.close_window(hw)
        except Exception as e:
            pass

    def activate(self, pattern):
        poss = self.get_matched_windows(pattern)
        if not poss:
            return Message('No matched application!')
        elif len(poss) == 1:
            self.activate_window_safely(poss[0][-1])
            return 'destroy'
        else:
            class DataActivate(Data):
                def run(slf, app, idx):
                    self.activate_window_safely(slf.data[idx][-1])
                    return 'destroy' if len(slf.data) == 1 else 'hold'
            return DataActivate(sorted(poss))

    def close(self, pattern):
        poss = self.get_matched_windows(pattern)
        if not poss:
            return Message('No matched application to close!')
        elif self.exact_match or len(poss) == 1:
            for win in poss:
                self.close_window_safely(win[-1])
            return 'destroy'
        else:
            class DataClose(Data):
                def run(slf, app, idx):
                    self.activate_window_safely(slf.data[idx][-1])
                    try:
                        self.close_window(slf.data[idx][-1])
                    except Exception as e:
                        pass
                    else:
                        self.activate_window_safely(self.current_window)

                    if len(slf.data) == 1:
                            return 'destroy'
                    slf.data = slf.data[:idx] + slf.data[idx+1:]
                    slf.init_ipage = app.popup.ipage
                    slf.init_index = idx
                    return slf
            return DataClose(sorted(poss))


class LazyApp:
    def __init__(self):
        self.app = None
        self.running = True

    def _show(self):
        if self.app and self.running:
            self.app._show()

    def update(self, app):
        self.app = app



if False:
    app = Travel()
    root = app.master
