#
# Timers for simple profiling
#
# (c) Copyright 2015 Jean-Olivier Irisson, GNU General Public License v3
#
#--------------------------------------------------------------------------

import time

# begin and end timers
def begin():
    x = time.time()
    return x

b = begin

def end(start, message=''):
    elapsed = time.time() - start
    message = message + ' (%f s)' % elapsed
    return message

e = end

# decorator for functions
def timer(func):
    def wrapper(*args, **kwargs):
        beg_ts = time.time()
        func(*args, **kwargs)
        end_ts = time.time()
        print("elapsed time: %f" % (end_ts - beg_ts))
    return wrapper
