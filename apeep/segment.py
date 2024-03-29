import logging

import numpy as np
import skimage.transform
import skimage.morphology
import skimage.measure
import skimage.filters

import apeep.timers as t

#from ipdb import set_trace as db

@t.timer
def segment(img, gray_threshold, dilate=3, erode=3,  min_area=150, max_area=400000):
    """
    Segment an image into particles
    
    Args:
        img (ndarray): image (of type float)
        gray_threshold (float): gray level threshold bellow which to consider particles
        dilate (int): after thresholding, particles are 'grown' by 'dilate' 
            pixels to include surrounding pixels which may be part of the object 
            but are not dark enough. NB: if Otsu's tresholding is used, `dilate` 
            is increased to `4/3*dilate`.
        erode (int): after thresholding, particles are 'shredded' by 'erode' 
            pixels to avoid including too many pixels. The combination of 
            dilation + erosion fills gaps in particles. 
        min_area (int): minimum number of pixels in a particle to consider it.
            NB: if Otsu's tresholding is used, `min_area` is increased to 
            `4/3*min_area`.
        max_area (int): maximum number of pixels in a particle to consider it.
            NB: this avoids the time-consuming segmentation of non relevant very large particles (streaks).
    
    Returns:
        ndarray: masked image (mask with each particle larger than `min_area` and smaller than
            `max_area` numbered as 1 and background as 0)
    """

    # threshold image
    img_binary = img < gray_threshold
    # pixels darker than threshold are True, others are False
        
    # perform morphological closing to fill gaps in particules
    img_binary = skimage.morphology.binary_dilation(img_binary, skimage.morphology.disk(dilate))
    img_binary = skimage.morphology.binary_erosion(img_binary, skimage.morphology.disk(erode))
        
    # label (i.e. find connected components of) particles and number them
    img_labelled = skimage.measure.label(img_binary, background=False, connectivity=2)
    
    # keep only large particles
    
    # # erase small regions from the labelled image
    # regions = skimage.measure.regionprops(img_labelled)
    # small_regions = [x for x in regions if fast_particle_area(x) < min_area]
    # img_labelled_large = img_labelled
    # for r in small_regions:
    #     img_labelled_large[r._slice] = img_labelled_large[r._slice] * (img_labelled_large[r._slice] != r.label)

    # recreate a labelled image with only large regions
    regions = skimage.measure.regionprops(img_labelled)
    large_regions = [r for r in regions if max_area >= fast_particle_area(r) > min_area]
    img_masked_large = np.zeros_like(img_labelled)
    
    for i in range(len(large_regions)):
        r = large_regions[i]
        img_masked_large[r._slice] = img_masked_large[r._slice] + r.image
    
    return(img_masked_large)

 
def fast_particle_area(x):
    return(np.sum(x._label_image[x._slice] == x.label))


def segmentation_threshold(img, method='auto', threshold=0.5, var_limit=0.0015):
    """
    Compute image gray level segmentation threshold according to chosen method. 
    
    Args:
        img (ndarray): image (of type float)
        method (str): string defining the method for thresholding.
            - 'static' considers `threshold` as a grey value in [0,100].
            - 'percentile' considers `threshold` as a percentile of grey levels,
              computed on the input image.
            - 'otsu' uses Otsu thresholding (and disregards the `threshold`
              argument).
            - 'q1' uses an affine transformation of q1 grey levels, and considers
              `threshold` as the y-intercept while slope is harcoded.
        threshold (flt): grey level or percentage; all pixels darker than 
            threshold will be considered as part of particles.
        var_limit (flt): value of the variance in the grey levels of the central
            part of `img` under which Ostu tresholding is used.
    
    Returns:
        float: gray segmentation threshold for given image
    """
    # get general logger
    log = logging.getLogger()

    if method == 'static':
        # convert value to be within [0,1]
        gray_threshold = threshold / 100.
    else:
        # Small image to compute thresholds if not generated by enhance        
        # crop and rescale image to compute the distribution of grey levels on 
        # the center of the image and an on a smaller one, which is both more
        # precise and faster
        crop = img.shape[0]//4
        img_c = img[crop:3*crop,:] # central band = more noise, fewer artifacts
        img_c_small = skimage.transform.rescale(img_c, 0.2, multichannel=False, anti_aliasing=False)

        if method == 'percentile':
            gray_threshold = np.percentile(img_c_small, (threshold))
        elif method == 'otsu':
            gray_threshold = skimage.filters.threshold_otsu(img_c_small)
        elif method == 'q1':
            q1 = np.percentile(img_c_small, 25)
            gray_threshold = 3.80 * q1 + threshold
        else:
            raise ValueError('unknown `method` argument')
    
    return gray_threshold