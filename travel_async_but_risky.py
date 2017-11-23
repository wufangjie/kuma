import os
import platform
import subprocess


try:
    path = os.path.split(os.path.realpath(__file__))[0]
except NameError:
    path = os.getcwd() or os.getenv('PWD')


if __name__ == '__main__':

    """
    The only two cases you are supposed to run this script:
    1. You killed kuma by accident
    2. kuma crashed
    """

    # FIXME: it is strange that this script can not work async in windows
    # but the same command I use to open a txt or other
    # rather than running another python script works finely


    PLATFORM = platform.system()

    if PLATFORM == 'Windows':
        py, filename = ['python',  'travel_for_windows.py']
    elif PLATFORM == 'Linux':
        py, filename = ['python3', 'travel_for_linux.py']
    elif PLATFORM == 'Darwin':
        py, filename = ['python3', 'travel_for_mac.py']
    else:
        raise Exception('Unknown platform!')

    p = subprocess.Popen(
        py + ' ' + os.path.join(path, filename),
        shell=True, start_new_session=True,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, universal_newlines=True)

    if PLATFORM == 'Linux':
        subprocess.call(['kill', str(p.pid)]) # kill sh -c ... process
