#
# Utility functions for dealing with images
#
# (c) 2019 Jean-Olivier Irisson, GNU General Public License v3

import numpy as np
import cv2

import apeep.timers as t

# from ipdb import set_trace as db

def asimg(x):
    """
    Convert numpy array into 8 bit image
    
    Args:
        x (ndarray): numpy array of floats in [0,1].
    
    Returns:
        ndarray: of uint8, in BGR order when the input is RGB.
    """
    # convert to 8 bit
    x_uint8 = (x * 255).astype(np.uint8)
    # if it is an RGB image, put the channels in BGR order, as expected by openCV
    if len(x.shape)==3 :
        x_uint8 = x_uint8[:,:,[2,1,0]]
    return(x_uint8)

# def show(x):
#     """
#     Display an array as image
#
#     Args:
#         x (ndarray): numpy array of floats in [0,1].
#     """
#     cv2.imshow("Image", asimg(x))
#     cv2.waitKey(0)
#     cv2.destroyAllWindows()
#     pass
def show(x):
    # cv2.imshow bugs
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
    cv2.imwrite(path, asimg(x))
    pass
