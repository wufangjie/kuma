from base import Message
from functools import reduce
import itertools
from itertools import *
import math
from math import *


def main(kuma, args):
    try:
        result = eval(args, globals())
    except Exception as e:
        return Message('Error: {}'.format(e))
    return Message('= {}'.format(result), 5000)
