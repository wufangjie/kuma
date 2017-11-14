import os
import platform
import subprocess


if __name__ == '__main__':

    """
    The only two cases you are supposed to run this script:
    1. You killed kuma by accident
    2. kuma crashed
    """

    # FIXME: it is strange that this script can not work async in windows
    # but the same command I use to open a txt or other
    # rather than running another python script works finely


    PLATFORM = platform.system() # {Linux Windows Darwin}

    try:
        path = os.path.split(os.path.realpath(__file__))[0]
    except NameError:
        path = os.getcwd() or os.getenv('PWD')

    filename = os.path.join(path, 'travel_for_{}.py'.format(PLATFORM.lower()))


    p = subprocess.Popen(
        ('python ' if PLATFORM == 'Windows' else 'python3 ') + filename,
        #['python' if PLATFORM == 'Windows' else 'python3', filename],
        shell=True, start_new_session=True,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, universal_newlines=True)

    try:
        _, err = p.communicate(timeout=1)
    except subprocess.TimeoutExpired:
        pass
    else:
        print(err)

    if PLATFORM == 'Linux':
        subprocess.call(['kill', str(p.pid)]) # kill sh -c ... process
