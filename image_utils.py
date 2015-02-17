
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
    img[:,:,3] = x - 255
    
    return img

def mask_image(image, mask):
    """
    Make composite image from a source image and mask
    
    image : ndarray
        ndarray
    mask : ndarray
        'binary' ndarray; pixels = 1 show, pixels = 0 do not
    """
    import numpy as np

    dims = image.shape

    output = np.zeros((dims[0], dims[1], 3))

    # make the mask a bit less "opaque"
    mask = np.where(mask == 0, 0.4, 1)
    output[:,:,0] = image * mask
    output[:,:,1] = image * mask
    output[:,:,2] = image
    
    return output

# TODO make a function: read next frame
    