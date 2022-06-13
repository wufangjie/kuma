import os
import time
import re
import logging
import pickle
from datetime import datetime, timedelta

from base import Message

from PyQt5.QtCore import QRunnable, Qt, QThreadPool, QThread, pyqtSignal

# check due date every X seconds (X should be greater than 1 to save CPU time)
UPDATE_INTERVAL = 1
logger = logging.getLogger(__name__)
REMINDER_FILE_NAME = 'reminders.pkl'
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
TIME_REG = re.compile(r'(\d+[dhms])')
TIME_UNIT_MAP = {'d':'days', 's':'seconds',  'm':'minutes', 'h':'hours', 'w':'weeks'}
DATETIME_REG = re.compile(r'\d{12,14}') # could be more complicated in the future


def load_object(filename):
    if not os.path.exists(filename):
        return None
    with open(filename, 'rb') as f:
        return pickle.load(f)

def save_object(obj, filename):
    with open(filename, 'wb') as output:  # Overwrites any existing file.
        pickle.dump(obj, output, pickle.HIGHEST_PROTOCOL)

class ReminderItem:
    def __init__(self, text, datetime):
        self.text = text
        self.datetime = datetime
        self.checked = False

    def check_validity(self):
        return

class Reminder:
    def __init__(self):
        self.items = []
        self.save_path = os.path.join(BASE_DIR, REMINDER_FILE_NAME)
        self.load()

    def load(self):
        try:
            obj = load_object(self.save_path)
            for item in obj:
                item.check_validity()
            self.items = obj
        except:
            pass

    def save(self):
        try:
            save_object(self.items, self.save_path)
        except Exception as e:
            logger.info("Failed to save to {} due to error {}".format(self.save_path, e))

    def check_time(self):
        due_items = []
        now = datetime.now()
        for item in self.items:
            if item.checked == False and now > item.datetime:
                due_items.append(item)
        for item in due_items:
            self.items.remove(item)
        self.save()
        return due_items

    def add(self, text, datetime):
        item = ReminderItem(text, datetime)
        self.items.append(item)
        self.save()

    def parse_date_str(self, date_str):

        # parse str such as '1d1h1m1s'
        time_strs = TIME_REG.findall(date_str)
        now = datetime.now()
        if len(time_strs) > 0:
            delay_dict = dict()
            for s in time_strs:
                d = int(s[:-1])
                name = TIME_UNIT_MAP[s[-1]]
                delay_dict[name] = d
            delay = timedelta(**delay_dict)
            target_date = now + delay
            return target_date
        m = DATETIME_REG.match(date_str)
        if m != None:
            target_date = None
            if len(date_str) == 14:
                target_date = datetime.strptime(date_str, '%Y%m%d%H%M%S')
            elif len(date_str) == 12:
                target_date = datetime.strptime(date_str, '%Y%m%d%H%M')
            if target_date != None:
                return target_date

        raise ValueError('Invalid date string')

    def add_by_command(self, command_arg):
        try:
            index = command_arg.find(' ')
            if index == -1:
                date_str = command_arg
                text = '无题'
            else:
                date_str = command_arg[:index]
                text = command_arg[index+1:]
            parsed_date = self.parse_date_str(date_str)
            self.add(text, parsed_date)
            return None
        except:
            return "无法识别:'{}..', 正确格式为0d0h0m0s或202107271800 + 提醒内容".format(command_arg[:4])

    def list(self):
        return self.items

class ReminderRunner(QThread):
    show_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.reminder = Reminder()
        self.interval = UPDATE_INTERVAL
        self.send_notification_func = None

    def connect(self, send_notification_func):
        self.show_message.connect(send_notification_func)

    def add_by_command(self, command_arg):
        return self.reminder.add_by_command(command_arg)

    def run(self):
        # Your long-running task goes here ...
        time.sleep(1)
        while True:
            due_items = self.reminder.check_time()
            if len(due_items) > 0:
                out_str = '提醒: '+';'.join([item.text for item in due_items])
                self.show_message.emit(out_str)
            time.sleep(self.interval)


reminder = ReminderRunner()

def main(kuma, args):
    if reminder.send_notification_func is None:
        reminder.connect(kuma.send_notification)
        reminder.start()
    msg = reminder.add_by_command(args)
    if msg != None:
        return Message(msg)#, ms=10000, action='kill')
    return 'destroy'

# just some test cases
if __name__ == '__main__':
    r = Reminder()
    print(r.parse_date_str('3d0h8h9d'))
    print(r.parse_date_str('1m'))
    print(r.parse_date_str('201806061800'))
    print(r.parse_date_str('20180606180003'))
    print(r.parse_date_str('coehunoheune3ohu'))
