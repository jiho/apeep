import numpy as np
# from skimage.io import imread
# from skimage.transform import resize

import skimage.transform
import skimage.morphology
import skimage.measure

import apeep.timers as t

# from ipdb import set_trace as db

@t.timer
def segment(img, method="percentile", threshold=0.1, dilate=3, min_area=500):
    """
    Segment an image into particles
    
    Args:
        img (ndarray): image (of type float)
        method (str): string defining the method for thresholding. 'percentile' 
            (the default) considers the argument `threshold` as a percentage of
            grey levels to consider as particles. 'static' considers
            `threshold` as a grey value in [0,100] directly.
        threshold (flt): percentage or grey level; all pixels darker than 
            threshold will be considered as part of particles.
        dilate (int): after thresholding, particles are "grown" by 'dilate' 
            pixels to include surrounding pixels which may be part of the
            object but are not dark enough.
        min_area (int): minimum number of pixels in an object to consider it.
    
    Returns:
        ndarray: labelled image (mask with each particle numbered as an integer)
    """

    if method == "percentile":
        # compute distribution of grey levels
        img_small = skimage.transform.rescale(img, 0.2, multichannel=False, anti_aliasing=False)
        # TODO check the speed improvement if this is computed only once, during image enhancement
        # define the new threshold
        threshold = np.percentile(img_small, (threshold))
    elif method == "static":
        # convert percentage into [0,1]
        treshold = threshold / 100.
    else:
        raise ValueError("unknown `method` argument")

    # threshold image
    img_binary = img < threshold
    # pixels darker than threshold are True, others are False

    # dilate dark regions, to encompass the surrounding, potentially important pixels
    if dilate >= 1 :
        img_binary = skimage.morphology.binary_dilation(img_binary, np.ones((dilate, dilate)))

    # TODO test assding contraction again

    # label (i.e. find connected components of) particles and number them
    img_labelled = skimage.measure.label(img_binary, background=False, connectivity=2)
    
    # detect large objects
    pixels_per_label = np.bincount(img_labelled.flat, weights=img_binary.flat)
    labels_of_large_pixel_count = np.where(pixels_per_label > min_area)
    # keep only those in the mask
    img_binary_large = np.isin(img_labelled, labels_of_large_pixel_count)
    # and as labels
    img_labelled_large = img_labelled * img_binary_large
    
    return(img_labelled_large)
 