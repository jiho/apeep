#
# Utility functions for dealing with images
#
# (c) 2019 Jean-Olivier Irisson, GNU General Public License v3

import numpy as np
import lycon

import apeep.timers as t

# from ipdb import set_trace as db

def asimg(x):
    """
    Convert numpy array into an image
    
    Not relevant with the lycon backend. Implemented for compatibility
    """
    return(x)

def show(x):
    # lycon cannot display images
    raise NotImplementedError
    pass

@t.timer
def save(x, path):
    _save(x, path)
    pass

def _save(x, path):
    """
    Save an array as an image
    
    Args:
        x (ndarray): numpy array of floats in [0,1].
    """
    lycon.save(path, x)
    pass
