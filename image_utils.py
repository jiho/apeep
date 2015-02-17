
def view(x, interactive=True):
    """
    Show a grey level image
    
    x : ndarray of dtype uint8
        a grey level image
    interactive : boolean
        when True, show the image in a non blocking way
    """
    from matplotlib import pyplot as p
    from pylab import cm
    if interactive:
        p.ion()
    else:
        p.ioff()
    p.imshow(x, cmap=cm.gray, interpolation='nearest')
    p.show()
    
    pass
#

def make_transparent_mask(mask, opacity=0.6):
    """
    Make a transparent red PNG image from a binary mask
    
    image : ndarray
        'binary' ndarray; 1 = background, 0 = regions of interest
    opacity : int in [0,1]
        opacity of the mask. 1 makes it fully opaque
        
    Returns
    alpha_mask : 4 dimensional ndarray
        the mask with channels BGRA.
    """
    import numpy as np

    # prepare an image + alpha channel of the same size (0=B, 1=G, 2=R, 3=alpha)
    dims = mask.shape    
    alpha_mask = np.ones((dims[0], dims[1], 4), dtype='uint8')
    
    # crank up the red channel
    alpha_mask[:,:,2] = alpha_mask[:,:,2] * 255
    
    # inverse the mask
    mask = np.where(mask == 1, 0, 1)
    # transform the provided mask into the alpha channel of the image
    alpha_mask[:,:,3] = mask * 255 * opacity
    
    return alpha_mask
#

def mask_image(image, mask):
    """
    Make composite image from a source image and its mask
    
    image : ndarray
        ndarray
    mask : ndarray
        'binary' ndarray; 1 = background, 0 = regions of interest
        
    NB: 'image' and 'mask' must have the same dimensions. This is not
        explicitly checked
    
    Returns
    masked : 3 dimensional ndarray
        colour image with channels BGR
    """
    import numpy as np

    # create an empty composite image
    dims = image.shape
    masked = np.zeros((dims[0], dims[1], 3))

    # make the mask a bit less "opaque"
    mask = np.where(mask == 0, 0.4, 1)
    
    # fill the composite image, not masking pixels in the red channel
    masked[:,:,0] = image * mask    # Blue
    masked[:,:,1] = image * mask    # Green
    masked[:,:,2] = image           # Red
    
    return masked
#

# TODO make a function: read next frame
    