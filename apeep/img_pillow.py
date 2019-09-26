#
# Utility functions for dealing with images
#
# (c) 2019 Jean-Olivier Irisson, GNU General Public License v3

import numpy as np
from PIL import Image

def asimg(x):
    xi = x * 255.
    img = Image.fromarray(xi.astype(np.uint8), mode="L")
    return(img)

def show(x):
    asimg(x).show()
    pass

def save(x, path):
    asimg(x).save(path)
    pass
