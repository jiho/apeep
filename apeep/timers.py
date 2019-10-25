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

def end(start):
    elapsed = time.time() - start
    return(elapsed)

e = end

def end_log(start, message=""):
    elapsed = time.time() - start
    log = logging.getLogger()
    log.debug(message + f" ({elapsed:.3f}s)")
    return(elapsed)

el = end_log

# decorator for functions
def timer(func):
    def wrapper(*args, **kwargs):
        log = logging.getLogger()
        start = time.time()
        out = func(*args, **kwargs)
        elapsed = time.time() - start
        log.debug(func.__name__ + f" ({elapsed:.3f}s)")
        return(out)
    return(wrapper)
