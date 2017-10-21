from base import Message
from functools import reduce
import itertools
from itertools import *
import math
from math import *

raise Exception('hello')

def main(params):
    try:
        result = eval(params, globals())
    except Exception as e:
        return Message('eval("{}"): {}'.format(params, e))
    return Message('eval("{}") = {}'.format(params, result), 5000)
