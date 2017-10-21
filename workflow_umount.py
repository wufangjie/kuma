from base import Data
import subprocess


class DataUmount(Data):
    def run(self, app, idx):
        msg = subprocess.getoutput(
            'umount ' + self.data[idx][0].split(' ', 1)[0])
        return 'destroy' if msg == '' else msg


def main(params):
    output = subprocess.getoutput('mount | grep -E ^/dev/sd[b-z] | sort')
    return DataUmount([(row, 'Dev') for row in output.split('\n')])
