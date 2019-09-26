#
# Timers for simple profiling
#
# (c) 2015 Jean-Olivier Irisson, GNU General Public License v3

import logging
import time

# from ipdb import set_trace as db

# begin and end timers
def begin():
    x = time.time()
    return x

b = begin

def end(start, message=''):
    elapsed = time.time() - start
    log = logging.getLogger()
    log.debug(message + " (%.3f s)" % elapsed)
    pass

e = end

# decorator for functions
def timer(func):
    def wrapper(*args, **kwargs):
        log = logging.getLogger()
        start = time.time()
        out = func(*args, **kwargs)
        elapsed = time.time() - start
        log.debug(func.__name__ + " (%.3f s)" % elapsed)
        return(out)
    return(wrapper)
