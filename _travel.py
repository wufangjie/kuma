from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtWidgets import QLineEdit, QLabel
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtWidgets import QShortcut, QAction
from PyQt5.QtWidgets import QStyle, QProxyStyle

from PyQt5.QtGui import QFont, QFontMetrics, QKeySequence, QIcon, QPixmap
from PyQt5.QtCore import Qt, QEvent, QTimer

import os
import re
import sys
import json
import time
import functools
import platform
import webbrowser
import subprocess
from collections import OrderedDict#, deque
from abc import abstractmethod
from base import Data, Message


app = QApplication.instance() # must before FM
if app is None:
    # if it does not exist then a QApplication is created (windows)
    app = QApplication(sys.argv)


########################################################################
# global variables
########################################################################
DEBUG = True#False#
PLATFORM = platform.system() # {'Linux', 'Windows', 'Darwin'}

try:
    PATH = os.path.split(os.path.realpath(__file__))[0]
except NameError:
    PATH = os.getcwd() or os.getenv('PWD')

def load_json(filename):
    with open(os.path.join(PATH, filename), 'rt', encoding='utf-8') as f:
        return json.load(f)


THEME = load_json('theme.json')
for key, val in THEME.items():
    if isinstance(val, (list, tuple)):
        THEME[key] = ' '.join(val)

FONT_NAME = THEME.get('font_name', 'Yuan Mo Wen')
font_size = THEME.get('font_size', 'default')
if font_size == 'default':
    PS = QFont(FONT_NAME).pointSize()
else:
    PS = int(font_size)
FONT_MAIN = QFont(FONT_NAME, PS << 1)
FONT_DESC = QFont(FONT_NAME, PS)
FM = QFontMetrics(FONT_MAIN)
PS1 = round(FM.height() / 3) # pixelSize
PS2 = PS1 << 1
PS3 = PS1 * 3
PS5 = PS1 * 5 # 2 + 3 = 5


QApplication.setStyle(THEME.get('app_style', 'Fusion')) # NOTE: for windows
if False:
    from PyQt5.QtWidgets import QStyleFactory
    print(QStyleFactory.keys()) # see more application styles

re_path = re.compile(r'^([A-Za-z]:|~|/)')


class CursorStyle(QProxyStyle):
    def __init__(self, tcw, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.tcw = int(tcw)
        except:
            self.tcw = 2

    def pixelMetric(self, metric, *args, **kwargs):
        if metric == QStyle.PM_TextCursorWidth:
            return self.tcw
        return super().pixelMetric(metric, *args, **kwargs)


########################################################################
# Row
########################################################################
class Row(QWidget):
    def __init__(self, master, index):
        super().__init__(master)
        self.master = master
        self.index = index

        self.left = self.make_component(FONT_MAIN, PS5)
        self.main = self.make_component(FONT_MAIN, PS3)
        self.desc = self.make_component(FONT_DESC, PS2)

        self.left.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.main.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.desc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.left.setStyleSheet(THEME.get('popup_left_style', ''))
        self.main.setStyleSheet(THEME.get('popup_main_style', ''))
        self.desc.setStyleSheet(THEME.get('popup_desc_style', ''))

        layout = QGridLayout()
        layout.addWidget(self.left, 0, 0, 2, 1) # rowspan, columnspan
        layout.addWidget(self.main, 0, 1)
        layout.addWidget(self.desc, 1, 1)
        layout.setSpacing(0)
        layout.setContentsMargins(5, 0, 5, 0) # (l, t, r, b) margin
        self.setLayout(layout)

    def make_component(self, font, height):
        comp = QPushButton(self)
        comp.setEnabled(False)
        comp.setFont(font)
        comp.setFixedHeight(height)
        return comp

    def hide(self):
        self.setHidden(True)

    def hide_desc(self):
        self.desc.setHidden(True)
        self.main.setFixedHeight(PS5)

    def show_desc(self):
        self.desc.setHidden(False)
        self.main.setFixedHeight(PS3)

    def highlight(self):
        self.setStyleSheet(THEME.get('highlight_style', ''))

    def unhighlight(self):
        self.setStyleSheet('')

    def update_data(self, data, lw, rw):
        self.main.setText(data.get('main', ''))
        self.main.setFixedWidth(rw)
        self.left.setText(data.get('left', ''))
        self.left.setFixedWidth(lw)
        desc = data.get('desc', '')
        if desc:
            self.desc.setText(desc)
            self.desc.setFixedWidth(rw)
            self.show_desc()
        else:
            self.hide_desc()
        self.setHidden(False)


########################################################################
# Popup
########################################################################
def movebd(func):
    """Move between data"""
    @functools.wraps(func)
    def wrapper(self, *args):
        if self.n_data:
            j_page, hl_pre = self.i_page, self.hl_pos
            if DEBUG:
                print('calling {}...'.format(func.__name__))
            func(self, *args)
            if j_page != self.i_page:
                self.update_display()
            if hl_pre != self.hl_pos:
                self.highlight(hl_pre=hl_pre)
        return 'break'
    return wrapper


class Popup(QWidget):
    def __init__(self, master):
        super().__init__(master)
        self.setHidden(True)
        self.master = master
        self.maxdisp = 9

        self.data = []
        self.i_page = 0
        self.n_page = 0
        self.n_data = 0
        self.hl_pos = 0 # in range(0, self.maxdisp)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.rows = []
        for i in range(self.maxdisp):
            self.rows.append(Row(self, i))
            layout.addWidget(self.rows[-1])
        self.setLayout(layout)
        #self.setStyleSheet('margin-left: 0.5em; margin-right: 0.5em;')

    def __bool__(self):
        return self.n_data > 0

    @property
    def hl_cur(self): # in range(0, self.n_data)
        return self.i_page * self.maxdisp + self.hl_pos

    @property
    def maxpos(self): # max position in current page
        if self.i_page == self.n_page:
            return (self.n_data - 1) % self.maxdisp
        else:
            return self.maxdisp - 1

    def update_display(self):
        i0 = self.i_page * self.maxdisp
        width = max([FM.width(d.get('left', ''))
                     for d in self.data[i0 : i0 + self.maxdisp]])
        if width:
            width += 22 # NOTE: padding-left + padding-right + 2
        rw = self.master.app_width - width
        for i in range(i0, min(i0 + self.maxdisp, self.n_data)):
            self.rows[i - i0].update_data(self.data[i], width, rw)
        for j in range(i - i0 + 1, self.maxdisp):
            self.rows[j].hide()
        self.setHidden(False)
        self.adjustSize()
        self.master.adjustSize()

    def update_data(self, data):
        self.data = data
        self.n_data = data.n_data
        self.n_page = (data.n_data - 1) // self.maxdisp
        self.i_page = data.hl_cur // self.maxdisp
        self.update_display()
        self.highlight(hl_new=(data.hl_cur % self.maxdisp))

    def quit(self):
        if self.n_data:
            self.n_data = 0
            #self.rows[self.hl_pos].unhighlight() # is it needed?
            self.setHidden(True)
            self.master.adjustSize()

    def highlight(self, hl_pre=None, hl_new=None):
        assert (hl_pre is None) ^ (hl_new is None)
        if hl_pre is None:
            self.rows[self.hl_pos].unhighlight()
            self.hl_pos = hl_new
        else:
            self.rows[hl_pre].unhighlight()
        self.rows[self.hl_pos].highlight()

    def run(self):
        if self.n_data:
            return self.data.run(self.master, self.hl_cur)

    @movebd
    def next_page(self):
        if self.i_page < self.n_page:
            self.i_page += 1
        if self.i_page == self.n_page:
            self.hl_pos = min(self.hl_pos, self.maxpos)

    @movebd
    def previous_page(self):
        if self.i_page > 0:
            self.i_page -= 1

    @movebd
    def beginning_of_data(self):
        self.i_page = 0
        self.hl_pos = 0

    @movebd
    def end_of_data(self):
        self.i_page = self.n_page
        self.hl_pos = self.maxpos

    @movebd
    def next_row(self):
        if (self.hl_pos < self.maxdisp - 1
            and self.hl_cur < self.n_data):
            self.hl_pos += 1

    @movebd
    def previous_row(self):
        if self.hl_pos > 0:
            self.hl_pos -= 1

    @movebd
    def beginning_of_rows(self):
        self.hl_pos = 0

    @movebd
    def end_of_rows(self):
        self.hl_pos = self.maxpos

    @movebd
    def move_to_golden_row(self):
        """Designed for fewest keystrokes"""
        n = sum([row.isVisible() for row in self.rows])
        if n > 7:
            m = 2
        elif n > 4:
            m = 1
        else:
            m = 0
        self.hl_pos = n - 1 - m if self.hl_pos < (n >> 1) else m


########################################################################
# Input
########################################################################
def move(func):
    @functools.wraps(func)
    def wrapper(self, *args):
        if DEBUG:
            print('calling {}...'.format(func.__name__)) # test calling
        func(self, *args)
        self.setCursorPosition(self.cursorPosition())
        # NOTE: set position is important for continuous calling
        if self.selected:
            self.select()
        self.master.hide_popup()
        self.pre_action = 'move'
    return wrapper


def kill(func):
    @functools.wraps(func)
    def wrapper(self, *args):
        self.save_state_if_needed()
        if DEBUG:
            print('calling {}...'.format(func.__name__))
        func(self, *args)
        if self.mark is not None:
            pos = self.cursorPosition()
            if pos < self.mark:
                self.mark = max(pos, self.mark - self.killed)
        self.save_state_if_needed()
        self.unselect()
        self.master.hide_popup()
        self.pre_action = (
            'delete' if func.__name__.endswith('_char') else 'kill')
    return wrapper


def unique(func):
    @functools.wraps(func)
    def wrapper(self, *args):
        if DEBUG:
            print('calling {}...'.format(func.__name__))
        func(self, *args)
        self.pre_action = func.__name__
    return wrapper


def save_unselect_and_quit(func):
    @functools.wraps(func)
    def wrapper(self, *args):
        self.save_state_if_needed()
        if DEBUG:
            print('calling {}...'.format(func.__name__))
        func(self, *args)
        self.save_state_if_needed()
        self.unselect()
        self.master.hide_popup()
        self.previous = func.__name__
    return wrapper


class Input(QLineEdit):
    # NOTE: setSelection() will change the cursor's position
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.clipboard = QApplication.clipboard()
        self.init_state()
        self.killed = 0
        self.setContextMenuPolicy(Qt.NoContextMenu) # disable rightclick
        # self.setPlaceholderText('Search')

        self.setStyle(CursorStyle(THEME.get('cursor_width', 2)))

        # os.environ['QT_IM_MODULE'] = 'fcitx'
        self.setAttribute(Qt.WA_InputMethodEnabled)
        self.setAttribute(Qt.WA_InputMethodTransparent)

        self.init_ui()

    def init_state(self):
        self.mark = None
        self.selected = False

        self.states = ['']
        self.positions = [0]
        self.state_idx = 0

        self.pre_action = '' # kill, undo, and others

    def init_ui(self):#, height=PS5, font=FONT_MAIN, style='default'):
        self.setMinimumWidth(self.master.app_width)
        self.setFixedHeight(PS5)
        self.setFont(FONT_MAIN)
        self.setStyleSheet(THEME.get('input_style', ''))

        #self.input.setMinimumWidth(self.width // 2)
        #self.input.setMaximumWidth(self.width * 3 // 4)

    def quit(self):
        self.init_state()
        # self.input.unselect()
        self.clear()

    def select(self):
        if self.mark is not None:
            self.selected = True
            self.setSelection(self.mark, self.cursorPosition() - self.mark)
            # the second param can be negative

    def unselect(self):
        if self.selected:
            self.selected = False
            self.deselect()

    def keyboard_insert(self, text):
        self.unselect() # self.deselect()
        if (self.mark is not None
            and self.cursorPosition() < self.mark):
            self.mark += len(text)
        self.insert(text) # TODO: add pre_action and save state sometimes
        self.pre_action = 'insert'
        if self.master.popup:
            if self.master.is_completing:
                if self.master.trie_last:
                    self.master.complete_keyword(text, False)
                else:
                    self.master.complete_path(self.get_text_before_cursor())
            else:
                self.master.hide_popup()

    def complete_insert(self, insert):
        self.unselect()
        text = self.text()
        n1, n2 = len(text), len(insert)
        i1, i2 = self.cursorPosition(), 0
        while i1 < n1 and i2 < n2:
            if text[i1] == insert[i2]:
                i1 += 1
                i2 += 1
            else:
                break
        self.setCursorPosition(i1)
        self.save_state_if_needed()
        self.insert(insert[i2:])
        self.save_state_if_needed()

    def get_text_before_cursor(self):
        return self.text()[:self.cursorPosition()]

    def save_state_if_needed(self):
        if self.states[-1] != self.text():
            self.states.append(self.text())
            self.positions.append(self.cursorPosition())
        else: # just move
            self.positions[-1] = self.cursorPosition()

    def clipboard_append(self, content):
        if self.pre_action != 'kill':
            self.clipboard.setText(content)
        else:
            self.clipboard.setText(self.clipboard.text() + content)

    def clipboard_appendleft(self, content):
        if self.pre_action != 'kill':
            self.clipboard.setText(content)
        else:
            self.clipboard.setText(content + self.clipboard.text())

    def get_char_type(self, char):
        if ('A' <= char <= 'Z') or ('a' <= char <= 'z'):
            return 'abc'
        elif '0' <= char <= '9':
            return 'num'
        # elif char in {' ', '\t', '\n'}:
        #     return 'spc'
        # elif char in {'/', ';', ',', '-', '_'}:
        #     return 'sep'
        elif 0x4e00 <= ord(char) <= 0x9fa6:
            return 'han'
        else:
            return 'thr'

    def word_end(self, step, text=None):
        start = self.cursorPosition() - (step < 0)
        if text is None:
            text = self.text()
        types = set()

        i = start
        str_end = len(text) if step > 0 else -1
        while (i - str_end) * step < 0:
            types.add(self.get_char_type(text[i]))
            if len(types) == 2:
                break
            i += step
        return abs(i - start)

    @move
    def backward_char(self):
        self.cursorBackward(False, 1)

    @move
    def forward_char(self):
        self.cursorForward(False, 1)

    @move
    def backward_word(self):
        # self.cursorWordBackward(False)
        self.cursorBackward(False, self.word_end(-1))

    @move
    def forward_word(self):
        # self.cursorWordForward(False)
        self.cursorForward(False, self.word_end(1))

    @move
    def beginning_of_line(self):
        #self.home(False)
        self.setCursorPosition(0)

    @move
    def end_of_line(self):
        self.end(False)

    @unique
    def keyboard_quit(self):
        self.master.hide_popup()
        self.unselect()

    @kill
    def delete_char(self):
        self.setSelection(self.cursorPosition(), 1)
        self.backspace()
        self.killed = 1

    @kill
    def backward_delete_char(self):
        self.backspace()
        self.killed = 1

    @kill
    def kill_word(self):
        pos = self.cursorPosition()
        self.killed = self.word_end(1)
        self.setSelection(pos, self.killed)
        self.clipboard_append(self.selectedText())
        self.backspace()

    @kill
    def backward_kill_word(self): # M-DEL
        pos = self.cursorPosition()
        self.killed = self.word_end(-1)
        self.setSelection(pos, -self.killed)
        self.clipboard_appendleft(self.selectedText())
        self.backspace()

    @kill
    def kill_line(self):
        pos = self.cursorPosition()
        text = self.text()
        self.clipboard_append(text[pos:])
        self.setText(text[:pos])
        self.killed = len(text) - pos

    @kill
    def backward_kill_line(self):
        """Emacs no such function"""
        pos = self.cursorPosition()
        self.setSelection(0, pos) # pos, 0 - pos)
        self.clipboard_appendleft(self.selectedText())
        self.backspace()
        self.killed = pos

    @unique
    def set_mark(self):
        self.mark = self.cursorPosition()
        self.unselect()
        self.selected = True

    @unique
    def exchange_point_and_mark(self):
        """TODO: Only break continuous kill, not undo?"""
        if self.mark is not None:
            pos = self.cursorPosition()
            self.selected = True
            if self.mark != pos:
                self.setCursorPosition(self.mark)
                self.mark = pos
                self.select()
                # if self.pre_action == 'kill':
                #     self.pre_action = 'exchange'

    @unique
    def select_all(self): # seems useless
        self.selectAll()
        self.mark = self.cursorPosition()
        self.setCursorPosition(0)
        self.selected = True

    @kill
    def select_all_and_cut(self): # seems useless
        #self.select_all()
        self.clipboard.setText(self.text())
        self.clear()

    @unique
    def mark_word(self): # M-@ -> M-h
        self.forward_word()
        self.set_mark()
        self.backward_word()

    @save_unselect_and_quit
    def capitalize_word(self):
        self.setSelection(self.cursorPosition(), self.word_end(1))
        text = self.selectedText()
        self.backspace()
        self.insert(text.capitalize())

    @save_unselect_and_quit
    def upcase_word(self):
        self.setSelection(self.cursorPosition(), self.word_end(1))
        text = self.selectedText()
        self.backspace()
        self.insert(text.upper())

    @save_unselect_and_quit
    def downcase_word(self):
        self.setSelection(self.cursorPosition(), self.word_end(1))
        text = self.selectedText()
        self.backspace()
        self.insert(text.lower())

    @save_unselect_and_quit
    def transpose_chars(self):
        pos = self.cursorPosition()
        if pos != 0:
            self.setSelection(pos - 1, 2)
            if len(self.selectedText()) == 1:
                if pos == 1: # only one character
                    self.setCursor(0)
                else:
                    self.setSelections(pos - 2, 2)
            text = self.selectedText()
            self.backspace()
            self.insert(text[::-1])

    @save_unselect_and_quit
    def copy(self):
        pos = self.cursorPosition()
        if self.mark is not None and self.mark != pos:
            text = self.text()
            self.clipboard.clear()
            if self.mark < pos:
                self.clipboard_append(text[self.mark : pos])
            else:
                self.clipboard_append(text[pos : self.mark])
            if not self.hasSelectedText(): # show selection if no highlight
                #self.setCursorPosition(self.mark)
                self.setSelection(pos, self.mark - pos)
                self.repaint()
                time.sleep(0.1)
                self.setCursorPosition(pos)

    @kill
    def cut(self):
        if self.mark is not None: # must not None
            pos = self.cursorPosition()
            self.setSelection(pos, self.mark - pos)
            self.killed = self.selectionLength()
            if self.mark > pos:
                self.clipboard_append(self.selectedText())
            else:
                self.clipboard_appendleft(self.selectedText())
            self.backspace()
        else:
            self.clipboard.clear()

    @save_unselect_and_quit
    def paste(self):
        self.mark = self.cursorPosition()
        self.insert(self.clipboard.text())

    # "yank": "M+y" # no need? kill ring is too complex!

    @unique
    def undo(self):
        if self.pre_action != 'undo':
            self.state_idx = len(self.states) - 1
            self.save_state_if_needed()
            self.unselect()

        if self.state_idx > 0:
            self.state_idx -= 1
            self.states.append(self.states[self.state_idx])
            self.positions.append(self.positions[self.state_idx])
            self.setText(self.states[-1])
            self.setCursorPosition(self.positions[-1])
            self.mark = None # if not, too complex


########################################################################
# Label, message
########################################################################
class Label(QPushButton):#QLabel):#
    def __init__(self, master):
        super().__init__(master)
        self.setHidden(True)
        self.setEnabled(False)
        self.setFont(FONT_MAIN)
        self.master = master

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setStyleSheet(THEME.get('message_style', ''))
        self.setFixedWidth(self.master.app_width)

        # self.setContentsMargins(5, 0, 5, 0) # did not work!
        # self.setWordWrap(True) # prefer controlling '\n' by self

        self.timer = QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.quit)

    def quit(self):
        self.setHidden(True)
        self.adjustSize()
        self.master.adjustSize()
        self.timer.stop()

    def update_data(self, msg):
        self.setText(msg.text)
        self.setHidden(False)
        self.adjustSize()
        self.master.adjustSize()
        if msg.action == 'hide':
            self.timer.start(int(msg.ms)) # <=0 means
        elif msg.action == 'kill':
            self.master.quit()
        else:
            pass


########################################################################
# DataComplete
########################################################################
class DataComplete(Data):
    def __init__(self, typ, data, hl_cur=0):
        super().__init__(data, hl_cur)
        self.typ = typ # {'key', 'dir'}

    def run(self, app, hl_cur):
        if self.typ == 'keyword':
            app.complete_insert(
                self.data[hl_cur].get('main', '')[app.trie_last['lv']:] + ' ')
        elif self.typ == 'path':
            app.complete_insert(self.data[hl_cur].get('real', ''))


class DataActivate(Data):
    def __init__(self, lst):
        super().__init__([
            {'left': left, 'main': main, 'desc': str(win), 'win': win}
            for left, main, wid, win in lst]) # TODO: str(win) or wid

    def run(self, app, idx):
        app.screen.activate_window_safely(self.data[idx]['win'])
        return 'destroy' if len(self.data) == 1 else 'hold'


class DataClose(Data):
    def __init__(self, lst):
        super().__init__([
            {'left': left, 'main': main, 'desc': str(win), 'win': win}
            for left, main, wid, win in lst])

    def run(self, app, idx):
        screen = app.screen
        closed = True
        try:
            screen.close_window(self.data[idx]['win'])
        except:
            screen.activate_window_safely(self.data[idx]['win'])
            try:
                screen.close_window(self.data[idx]['win'])
            except:
                closed = False
        app.activateWindow()
        # activated = screen.activate_window_safely(screen.current_window)
        # print('kuma activated: {}'.format(activated))
        #app._show() # useless TODO: activate kuma
        if closed:
            if self.n_data == 1:
                return 'destroy'
            self.data = self.data[:idx] + self.data[idx+1:]
            self.n_data -= 1
            self.hl_cur = min(self.n_data - 1, app.popup.hl_cur)
        return self


class KeyTrie:
    """
    space for time, slow build, fast complete
    value: {'Keyword': '', 'Type': '', ...}
    """
    def __init__(self, master):
        self.master = master
        self._dict = {'all': [], 'key': None, 'lv': 0}

    def __contains__(self, word):
        return '#' in self.startswith(word)

    def startswith(self, word):
        _dict = self._dict
        for w in word:
            if w not in _dict:
                return {}
            _dict = _dict[w]
        return _dict

    def _update_nxt(self, dct, w):
        # NOTE: next character, '' means >1
        if dct['nxt'] is None:
            dct['nxt'] = w
        elif dct['nxt'] != '' and dct['nxt'] != w:
            dct['nxt'] = ''

    def insert(self, word, value):
        _dict = self._dict
        for i, w in enumerate(word):
            if w not in _dict:
                _dict[w] = {'all': [], 'nxt': None, 'lv': i + 1}
            _dict['all'].append(value)
            self._update_nxt(_dict, w)
            _dict = _dict[w]
        self._update_nxt(_dict, '')
        _dict['#'] = value
        _dict['all'].append(value)

    def inserts(self, lst):
        for key, val in lst:
            self.insert(key, val)

    def complete(self, prefix, last_dict=None):
        _dict = last_dict or self._dict
        lv = _dict['lv']
        for w in prefix:
            if w not in _dict:
                return '', None
            _dict = _dict[w]
        if len(_dict['all']) == 1:
            return _dict['all'][0]['Keyword'][lv + len(prefix):] + ' ', None
        ret = []
        while _dict['nxt']:
            ret.append(_dict['nxt'])
            _dict = _dict[_dict['nxt']]
        return ''.join(ret), _dict

    def clear(self):
        self._dict = {'all': [], 'nxt': None, 'lv': 0}


########################################################################
# App
########################################################################
class Travel(QWidget):
    def __init__(self, screen):
        super().__init__()
        self.screen = screen
        desktop = QApplication.desktop()
        self.dw = desktop.width()
        self.dh = desktop.height()
        self.dx = self.dw // 75 # for window move
        self.dy = self.dh // 75 # for window move
        # self.setGeometry(self.dw // 4, self.dh >> 2, self.dw >> 1, 1)
        self.setGeometry(self.dw // 4, self.dh >> 2, 0, 0)

        self.app_width = self.dw >> 1

        self.setWindowTitle('kuma')
        self.setStyleSheet(THEME.get('global_style', ''))
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint)
        # self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.setMinimumWidth(self.dw >> 1)
        # self.setMaximumWidth(self.dw * 3 // 4)

        self.input = Input(self)
        self.popup = Popup(self)
        #self.rows = self.popup.rows
        self.label = Label(self)

        layout = QVBoxLayout()
        layout.addWidget(self.input)
        layout.addWidget(self.popup)
        layout.addWidget(self.label)
        layout.setSpacing(0) # between input and popup
        self.setLayout(layout)

        self.shortcuts = {}
        self.bind_shortcuts()

        self.config_mtime = 0
        self.config_file = os.path.join(PATH, 'config.json')
        self.trie = KeyTrie(self)
        self.trie_last = None
        self.load_config()

        self.disks = []#set()
        if PLATFORM == 'Linux':
            self.open_file_cmd = self.open_dir_cmd = 'xdg-open'
        elif PLATFORM == 'Windows':
            self.open_file_cmd = 'call'
            self.open_dir_cmd = 'start'

            for c in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
                temp = '{}:/'.format(c)
                if os.path.isdir(temp):
                    self.disks.append(temp)

        elif PLATFORM == 'Darwin':
            self.open_file_cmd = self.open_dir_cmd = 'open'
        else:
            raise Exception('Unsupport Platform: {}'.format(PLATFORM))

        self.running = True

        icon = QIcon()
        if self.dw > 4000:
            p = 512
        elif self.dw > 2000:
            p = 256
        elif self.dw > 1000:
            p = 128
        else:
            p = 64
        icon.addPixmap(
            QPixmap(os.path.join(PATH, 'icon', 'kuma({0}x{0}).png'.format(p))),
            QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)

    @property
    def is_completing(self):
        return self.popup and isinstance(self.popup.data, DataComplete)

    def load_config(self):
        mt = os.path.getmtime(self.config_file)
        if self.config_mtime != mt:
            self.trie.clear()
            self.trie_last = None
            with open(self.config_file, 'rt', encoding='utf-8') as f:
                config = json.load(f)
            keyword_set = set()
            for typ, lst in config.items():
                temp = []
                for dct in lst:
                    if PLATFORM not in dct.get('Platform', PLATFORM):
                        continue
                    if 'Keyword' not in dct:
                        return self.show_message('No Keyword!')
                        #raise Exception('No Keyword!')
                    dct['Type'] = typ
                    key = dct['Keyword']
                    if key in keyword_set:
                        return self.show_message(
                            'Make sure the keywords are unique!')
                        #raise Exception('Make sure the keywords are unique!')
                    keyword_set.add(key)
                    temp.append([key, dct])
                self.trie.inserts(sorted(temp))
            self.config_mtime = mt

    def hide_popup(self):
        self.popup.quit()

    def eventFilter(self, source, event):
        if event.type() == QEvent.ShortcutOverride:
            sequence = QKeySequence(int(event.modifiers()) + event.key())
            if sequence in self.shortcuts:
                # self.shortcuts[sequence]() # add this, will call twice
                return True # just like tk's "break"?
        elif event.type() == QEvent.KeyPress:
            text = event.text()
            if text:
                self.input.keyboard_insert(text)
                return True
        elif event.type() == QEvent.InputMethod:
            if self.is_completing:
                text = event.commitString()
                if text:
                    self.input.keyboard_insert(text)
                    return True
        # elif event.type() == QEvent.UpdateRequest:
        #     if self.input.selected:
        #         self.input.select()
        return super().eventFilter(source, event)

    def _bind_ks(self, ks, func, kind='shortcut'):
        if kind == 'shortcut':
            temp = QShortcut(QKeySequence(ks), self)
            #, context=Qt.ApplicationShortcut)
            temp._func = func
            # try:
            #     temp.disconnect() # useless for QLineEdit standard keybinding
            # except TypeError:
            #     pass
            temp.activated.connect(func)#, type=Qt.UniqueConnection)
            key = temp.key()
        else:
            temp = QAction(self) # this way, function carry an event parameter
            temp.setShortcut(ks)
            # try:
            #     temp.disconnect() # useless for QLineEdit standard keybinding
            # except TypeError:
            #     pass
            temp.triggered.connect(func)
            self.addAction(temp)
            key = temp.shortcut()
            func = temp.trigger
        assert key not in self.shortcuts
        self.shortcuts[key] = func
        return temp

    def bind_shortcuts(self):
        self.shortcuts_for_human = OrderedDict()
        for comp, dct in load_json('shortcuts.json').items():
            obj = self.__dict__.get(comp, self)
            for func, ks in dct.items():
                if func in obj.__class__.__dict__:
                    self.__dict__['sc_{}'.format(func)] = self._bind_ks(
                        ks, functools.partial(
                            obj.__class__.__dict__[func], obj))
                    self.shortcuts_for_human[ks] = func
        self.sc_Return = self._bind_ks('Return', self.run)
        self.sc_Enter = self._bind_ks('Enter', self.run) # 小键盘
        self.sc_Tab = self._bind_ks('Tab', self.complete)

    def quit(self):
        if not self.isHidden():
            self.input.quit()
            self.popup.quit()
            self.setHidden(True)

    def activate_safely(self):
        if not self.isActiveWindow():
            self.activateWindow()
            self.input.clearFocus()
            self.input.setFocus()#Qt.MouseFocusReason)

    def _show(self):
        # if not self.isHidden(): # TODO: is it can fix focus problem?
        #     self.setHidden(True)
        self.setHidden(False)
        self.activate_safely()

    def dummy(self):
        """Bind shortcuts your want to disable"""
        pass

    def move_window(self, dx=0, dy=0):
        rect = self.geometry()
        if dx:
            rect.setX(rect.x() + dx)
        if dy:
            rect.setY(rect.y() + dy)
        self.setGeometry(rect)
        self.adjustSize()

    def window_up(self):
        self.move_window(dy=-self.dy)

    def window_down(self):
        self.move_window(dy=self.dy)

    def window_left(self):
        self.move_window(dx=-self.dx)

    def window_right(self):
        self.move_window(dx=self.dx)

    def show_message(self, msg):
        if isinstance(msg, str):
            msg = Message(msg)
        self.label.update_data(msg)

    def complete(self):
        self.pre_action = 'tab'
        if self.popup:
            self.popup.run()
            self.popup.quit()
        else:
            text = self.input.get_text_before_cursor()
            if self.is_path(text):
                self.trie_last = None
                self.complete_path(text)
            else:
                self.complete_keyword(text)

    def is_path(self, text):
        return re_path.match(text)

    def complete_path(self, text):
        i0 = self.input.cursorPosition()
        if PLATFORM == 'Windows':
            if text == '/':
                data = [{'left': 'D', 'main': '/' + d, 'real': d} for d in self.disks]
                self.popup.update_data(DataComplete('path', data))
                return
            elif text.startswith('/'):
                text = text[1:]
                i0 -= 1
            if len(text) == 1:
                if text.upper() + ':/' in self.disks:
                    self.complete_insert(':/')
                self.popup.quit()
                return
            elif len(text) == 2 and text[-1] == ':':
                text += '/'

        if text.startswith('~'):
            home = os.path.expanduser('~')
            i0 += len(home) - 1
            text = home + text[1:]
        else:
            home = ''
        if os.path.isdir(text) and os.path.split(text)[1] not in {'.', '..'}:
            # NOTE: ~/. is a dir ..
            base, prefix = text, ''
        else:
            base, prefix = os.path.split(text)

        dirs, prefix = self.listdir(base, prefix)
        if not dirs:
            self.popup.quit()
        elif len(dirs) == 1:
            self.complete_insert(os.path.join(base, dirs[0])[i0:])
            self.popup.quit()
        else:
            short = '~' + base[len(home):] if home else base
            if len(short) > 20:
                short = os.path.join('...', os.path.split(base)[1])
                # 太长的话, 只显示两层? 之前用 .../ 表示
            data = []
            lp = len(prefix)
            hl_cur = 0
            for i, d in enumerate(dirs):
                real = d[lp:]
                if not real:
                    hl_cur = i
                data.append({'left': 'D' if d.endswith('/') else '-',
                             'main': os.path.join(short, d),
                             'real': real})
            self.complete_insert(os.path.join(base, prefix)[i0:])
            self.popup.update_data(DataComplete('path', data, hl_cur))

    def longest_common_prefix(self, lst):
        if not lst:
            return ''
        elif len(lst) == 1:
            return lst[0]
        ret = []
        for c1, c2 in zip(lst[0], lst[-1]): # NOTE: lst is sorted
            if c1 == c2:
                ret.append(c1)
            else:
                break
        return ''.join(ret)

    def listdir(self, dirname, prefix=''):
        for root, dirs, files in os.walk(dirname):
            if prefix:
                dirs = [d + '/' for d in dirs if d.startswith(prefix)]
                files = [d for d in files if d.startswith(prefix)]
            else:
                dirs = [d + '/' for d in dirs]
            if dirs:
                prefix = self.longest_common_prefix(dirs)
                if files:
                    prefix = self.longest_common_prefix([
                        prefix,
                        self.longest_common_prefix(files)])
            else:
                prefix = self.longest_common_prefix(files)
            return sorted(dirs) + sorted(files), prefix
        return [], ''

    def complete_keyword(self, text, renew=True):
        self.load_config()
        if renew:
            self.trie_last = None
        insert, dct = self.trie.complete(text, self.trie_last)
        self.complete_insert(insert)
        self.trie_last = dct
        if dct is None:
            self.popup.quit()
        else:
            data = []
            for dct in dct['all']:
                data.append({'left': dct.get('Type', ''),
                             'main': dct.get('Keyword', ''),
                             'desc': (dct.get('Description')
                                      or dct.get('Pattern')
                                      or dct.get('Command', ''))})
            self.popup.update_data(DataComplete('keyword', data))

    def complete_insert(self, insert):
        self.input.complete_insert(insert)

    def run(self):
        action = self._run()
        self.pre_action = 'run'
        if action == 'hold':
            pass
        elif action == 'destroy':
            self.quit()
        elif isinstance(action, Data) and len(action):
            self.popup.update_data(action)
        elif isinstance(action, Message):
            self.show_message(action)
        else:
            self.popup.quit()

    def _run(self):
        if self.popup:
            return self.popup.run()

        text = self.input.text()
        if self.is_path(text):
            shell = True if PLATFORM == 'Windows' else False
            if text.startswith('~'):
                text = os.path.expanduser(text)
            if os.path.isdir(text):
                return self._subprocess_popen(
                    [self.open_dir_cmd, text], shell=shell)
            elif os.path.isfile(text):
                return self._subprocess_popen(
                    [self.open_file_cmd, text], shell=shell)
            else:
                return self.complete_path(text[:self.input.cursorPosition()])

        text = text.rstrip()
        if ' ' in text:
            key, args = text.split(' ', 1)
        else:
            key, args = text, ''
        dct = self.trie.startswith(key)
        if dct:
            if '#' in dct:
                dct = dct['#']
                typ = dct['Type']
                args = args.strip()
                if typ == 'Web':
                    return self._get_url(dct['Command'], args)
                elif typ == 'App':
                    return self._activate_or_open(key, args, dct)
                elif typ == 'Py':
                    return self._run_workflow(key, args)
                elif typ == 'Sp':
                    return self._process_sp(key, args)
                else:
                    return self.show_message(
                        'Unknown keyword type: {}!'.format(typ))
            else:
                self.input.setCursorPosition(len(key))
                self.complete_keyword(key)
        else:
            self.show_message('Unknown keyword!')

    def _get_url(self, cmd, args):
        sp = args.rsplit(' ', 1)[-1].lower()
        if sp == '-c':
            webbrowser.get('google-chrome').open_new_tab(cmd.format(args[:-3]))
        elif sp == '-f':
            webbrowser.get('firefox').open_new_tab(cmd.format(args[:-3]))
        else:
            webbrowser.open_new_tab(cmd.format(args))
        return 'destroy'

    def _activate_or_open(self, key, args, dct):
        cmd = dct['Command']
        if args.rsplit(' ', 1)[-1].lower() == 'new':
            return self._subprocess_popen(
                '{} {}'.format(cmd, args[:-4]), shell=True)
        for pattern in [dct.get('Pattern', ''), key]:
            if pattern:
                ret = self.screen.activate(pattern)
                if not isinstance(ret, Message):
                    return ret
        return self._subprocess_popen(
            '{} {}'.format(cmd, args), shell=True)

    def _run_workflow(self, key, args):
        dct = {}
        try:
            exec('from workflow_{} import main'.format(key), dct)
        except Exception as e:
            return Message(repr(e))
        return dct['main'](args)

    def _process_sp(self, key, args):
        if key == 'activate':
            return self.screen.activate(args)
        elif key == 'close':
            return self.screen.close(args)
        elif key == 'toggle-search-engine':
            self.search_engine ^= 1
            return Message('{} is used!'.format(self.search_engine_name),
                           ms=250)
        elif key == 'shortcuts':
            return Data([{'left': ks, 'main': func}
                         for ks, func in self.shortcuts_for_human.items()])
        else:
            return Message('Unimplemented sp-keyword: {}!'.format(key))

    def _subprocess_popen(self, cmd, shell):
        p = subprocess.Popen(cmd, shell=shell, start_new_session=True,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, universal_newlines=True)
        try:
            _, err = p.communicate(timeout=0.1) # 0.1s
        except subprocess.TimeoutExpired:
            err = ''

        if PLATFORM == 'Linux':
            pass
            #subprocess.call(['kill', str(p.pid)]) # kill sh -c ... process
        if err:
            return Message(err.strip())
        else:
            return 'destroy'

    def add_listener(self, hotkey_thread):
        self.listener = hotkey_thread
        self.listener._show.connect(self._show)


class BaseScreen:
    def get_matched_windows(self, pattern):
        self.exact_match = False
        poss = self.get_windows()
        if pattern:
            ret = [win for win in poss
                   if pattern in {win[0].lower(), win[1].lower()}]
            if ret:
                self.exact_match = True
                return ret

            pattern = re.compile(pattern, re.IGNORECASE)
            ret = [win for win in poss if pattern.search(win[0])]
            if ret:
                return ret
            return [win for win in poss if pattern.search(win[1])]
        return poss

    @abstractmethod
    def get_windows(self):
        """Return list of (app_name, pid, title, hw) tuple
        +NOTE: important! RECORD current window+
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
            return True
        except:
            return False

    def close_window_safely(self, hw):
        try:
            self.close_window(hw)
        except:
            pass

    def activate(self, pattern):
        poss = self.get_matched_windows(pattern)
        if not poss:
            return Message('No matched application!')
        elif len(poss) == 1:
            self.activate_window_safely(poss[0][-1])
            return 'destroy'
        else:
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
            return DataClose(sorted(poss))


def main(kuma, hotkey_thread):
    kuma.add_listener(hotkey_thread)
    app.installEventFilter(kuma)
    if PLATFORM == 'Windows':
        kuma.input.insert('shortcuts') # speed up the first boot
        kuma.input.clear()
        kuma._show()
    #kuma.show()
    #kuma.quit()
    kuma.listener.start()
    try:
        __file__
    except NameError:
        if PLATFORM != 'Windows':
            return
    sys.exit(app.exec_())


if __name__ == '__main__':

    self = Travel(BaseScreen())
    self.show()
    app.installEventFilter(self)

# NOTE: use QThread and pyqtSignal instead of threading.Thread

# DONE: TODO: inserting when selected
# DONE: TODO: change input cursor's width
# DONE? TODO: find a better delete way?
# DONE: TODO: disable rightclick
# DONE: TODO: 当 mark 在 cursor 之后, 输入字符需要把 mark 往后移, 删除同理, 如果删除包含了 mark, 那么新 mark 位于删除的最前面
# DONE? TODO: cut 与 连续删除的关系
# DONE: TODO: 中文输入法支持

# TODO: shortcut for topmost?
# TODO: 解除无用的快捷键, 防止误用
