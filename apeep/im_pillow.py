#
# Utility functions for dealing with images
#
# (c) 2019 Jean-Olivier Irisson, GNU General Public License v3

import numpy as np
from PIL import Image

import apeep.timers as t

# from ipdb import set_trace as db

def read(path):
    """
    Read a greyscale image into a numpy array
    
    Args:
        path (str): path to the image
    
    Returns:
        ndarray: of float in [0,1]
    """
    x = np.array(Image.open(path))
    return(x / 255.)

def asimg(x):
    """
    Convert numpy array into 8 bit Pillow image
    
    Args:
        x (ndarray): numpy array of floats in [0,1].
    
    Returns:
        Image: Pillow image.
    """
    # convert to 8 bit
    x_uint8 = (x * 255).astype(np.uint8)
    # convert into a pillow image
    img = Image.fromarray(x_uint8)
    return(img)

def show(x):
    """
    Display an array as image
    
    Args:
        x (ndarray): numpy array of floats in [0,1].
    """
    asimg(x).show()
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
    asimg(x).save(path)
    pass
