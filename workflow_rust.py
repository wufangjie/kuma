from base import Message
from rust_eval import rust_eval
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def main(kuma, args):
    try:
        result = rust_eval(args)
        os.chdir(BASE_DIR)
    except Exception as e:
        os.chdir(BASE_DIR)
        return Message('Error: {}'.format(e))
    lines = result.splitlines()[2:]
    if lines[0].strip().startswith('Running '):
        lines = lines[1:]
    result = '\n'.join(lines)
    return Message('= {}'.format(result), 10000)

