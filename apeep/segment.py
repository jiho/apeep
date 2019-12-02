import logging

import numpy as np
import skimage.transform
import skimage.morphology
import skimage.measure
import skimage.filters

import apeep.timers as t

# from ipdb import set_trace as db

@t.timer
def segment(img, method="auto", threshold=0.5, var_limit=0.0015, dilate=3, erode=3,  min_area=150):
    """
    Segment an image into particles
    
    Args:
        img (ndarray): image (of type float)
        method (str): string defining the method for thresholding.
            - 'static' considers `threshold` as a grey value in [0,100].
            - 'percentile' considers `threshold` as a percentile of grey levels,
              computed on the input image.
            - 'otsu' uses Otsu thresholding (and disregards the `threshold`
              argument).
            - 'auto' uses Otsu thresholding for sufficiently clean images
              and falls back to 'percentile' thresholding for noisy images
             (because Otsu thresholding results in too many particles in that
             case). The switch is determined by `var_limit`.
        threshold (flt): grey level or percentage; all pixels darker than 
            threshold will be considered as part of particles.
        var_limit (flt): value of the variance in the grey levels of the central
            part of `img` under which Ostu tresholding is used.
        dilate (int): after thresholding, particles are "grown" by 'dilate' 
            pixels to include surrounding pixels which may be part of the object 
            but are not dark enough. NB: if Otsu's tresholding is used, `dilate` 
            is increased to `4/3*dilate`.
        erode (int): after thresholding, particles are "shredded" by 'erode' 
            pixels to avoid including too many pixels. The combination of 
            dilation + erosion fills gaps in particles. 
        min_area (int): minimum number of pixels in a particle to consider it.
            NB: if Otsu's tresholding is used, `min_area` is increased to 
            `4/3*min_area`.
    
    Returns:
        ndarray: labelled image (mask with each particle larger than `min_area` 
            numbered as an integer)
    """
    # get general logger
    log = logging.getLogger()

    if method == "static":
        # convert value to be within [0,1]
        treshold_0_1 = threshold / 100.
    else:
        # crop and rescale image to compute the distribution of grey levels on 
        # the center of the image and an on a smaller one, which is both more
        # precise and faster
        crop = round(img.shape[0]/4)
        img_center = img[crop:3*crop,:] # central band = more noise, fewer artifacts
        img_center_small = skimage.transform.rescale(img_center, 0.2, multichannel=False, anti_aliasing=False)
        
        # Small image to compute thresholds
        img_small = skimage.transform.rescale(img, 0.2, multichannel=False, anti_aliasing=False)
        # TODO check the speed improvement if this is computed only once, during image enhancement

        if method == "auto":
            # compute grey level variance on centered small version of non enhanced image
            grey_var = img_center_small.var()
            # for noisy images, use percentile thresholding, for clean ones use otsu
            if grey_var > var_limit:
                log.debug("noisy image, switching to percentile tresholding")
                method = "percentile"
            else:
                method = "otsu"

        if method == "percentile":
            threshold_0_1 = np.percentile(img_small, (threshold))
        elif method == "otsu":
            threshold_0_1 = skimage.filters.threshold_otsu(img_small)
            # increase dilate for Otsu
            dilate = round(4/3 * dilate)
            
            # increase min_area for Otsu
            min_area = round(4/3 * min_area)
        else:
            raise ValueError("unknown `method` argument")

    # threshold image
    img_binary = img < threshold_0_1
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
    large_regions = [r for r in regions if fast_particle_area(r) > min_area]
    img_labelled_large = np.zeros_like(img_labelled)
    for r in large_regions:
        img_labelled_large[img_labelled == r.label] = r.label
    
    return(img_labelled_large)

 
def fast_particle_area(x):
    return(np.sum(x._label_image[x._slice] == x.label))
