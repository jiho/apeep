#
# Utility functions for dealing with images
#
# (c) 2019 Jean-Olivier Irisson, GNU General Public License v3

import numpy as np
import lycon

import apeep.timers as t

# from ipdb import set_trace as db

@t.timer
def save(x, path):
    lycon.save(path, x)
    pass
