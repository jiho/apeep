
def view(x, interactive=True):
    """quick function to show a grey level image"""
    from matplotlib import pyplot as p
    from pylab import cm
    if interactive:
        p.ion()
    else:
        p.ioff()
    p.imshow(x, cmap=cm.gray, interpolation='nearest')


def make_mask_image(x, intensity=150):
    """
    Make a transparent red PNG image from a binary mask
    
    x : ndarray
        'binary' ndarray; pixels = 1 show, pixels = 0 do not
    intensity : int
        intensity of the mask. 255 makes it fully opaque
    """
    import numpy as np

    dims = x.shape
    
    # prepare an image + alpha channel of the same size
    img = np.ones((dims[0], dims[1], 4), dtype='uint8')
    
    # crank up the red channel
    img[:,:,2] = img[:,:,2] * 255
    
    # transform the provided mask into the alpha channel of the image
    img[:,:,3] = x * intensity
    
    return img
    