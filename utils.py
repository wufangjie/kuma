import os
import json
import subprocess
import platform


PLATFORM = platform.system() # {'Linux', 'Windows', 'Darwin'}

try:
    PATH = os.path.split(os.path.realpath(__file__))[0]
except NameError:
    PATH = os.getcwd() or os.getenv('PWD')


def load_json(filename, path=PATH):
    """Load json in current path"""
    with open(os.path.join(path, filename), 'rt', encoding='utf-8') as f:
        return json.load(f)



def run_script(cmd, shell=True):
    p = subprocess.Popen(cmd, shell=shell, start_new_session=True,
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, universal_newlines=True)
    try:
        _, err = p.communicate(timeout=0.1) # 0.1s
    except subprocess.TimeoutExpired:
        err = ''

    # if PLATFORM == 'Linux':
    #     pass
    #     # subprocess.call(['kill', str(p.pid)]) # kill sh -c ... process
    if err:
        return Message(err.strip())
    else:
        return 'destroy'


def run_apple_script(cmd, shell=True):
    return run_script("osascript -e '{}'".format(cmd, True))
