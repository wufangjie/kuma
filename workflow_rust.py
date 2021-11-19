from base import Message
from rust_eval import rust_eval

def main(kuma, args):
    try:
        result = rust_eval(args)
    except Exception as e:
        return Message('Error: {}'.format(e))
    print(result)
    return Message('= '.format(result), 5000)

