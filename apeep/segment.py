import numpy as np
import skimage.transform
import skimage.morphology
import skimage.measure
import skimage.filters

import apeep.timers as t

# from ipdb import set_trace as db

@t.timer
def segment(enhanced_img, img, method="auto", threshold=0.4, auto_threshold = 0.0015, adapt_closing=5, otsu_closing = 8, min_area=150):
    """
    Segment an image into particles
    
    Args:
        img (ndarray): image (of type float)
        method (str): string defining the method for thresholding. 'percentile' 
            (the default) considers the argument `threshold` as a percentage of
            grey levels to consider as particles. 'static' considers
            `threshold` as a grey value in [0,100] directly. 'auto' uses 
            'percentile' thresholding for noisy images (thermocline) and otsu
            thresholding for clear images.
        threshold (flt): percentage or grey level; all pixels darker than 
            threshold will be considered as part of particles.
        auto_threshold (flt): value of grey level variance for which segmentation 
            method changes. Images with lower variance are segmented with Otsu, 
            images with higher variance are segmented with 'percentile' method.
            Computed on non enhanced image. 
        adapt_closing (int): after adaptative thresholding, particles are "closed" by running a 
            dilatation of 'adapt_closing' pixels followed by an erosion of 'adapt_closing' pixels to
            fill potentiel gaps in particles
        otsu_closing (int): after otsu thresholding, particles are "closed" by running a 
            dilatation of 'adapt_closing' pixels followed by an erosion of 'adapt_closing' pixels to
            fill potentiel gaps in particles
        min_area (int): minimum number of pixels in an object to consider it.
    
    Returns:
        ndarray: labelled image (mask with each particle numbered as an integer)
    """

    if method == "percentile":
        # compute distribution of grey levels
        en_img_small = skimage.transform.rescale(enhanced_img, 0.2, multichannel=False, anti_aliasing=False)
        # TODO check the speed improvement if this is computed only once, during image enhancement
        # define the new threshold based on percentile
        threshold = np.percentile(en_img_small, (threshold))
        
        # threshold image
        img_binary = enhanced_img < threshold
        
        # perform morphological closing to fill gaps in particules
        img_binary = skimage.morphology.binary_closing(img_binary, np.ones((adapt_closing, adapt_closing)))
        
        
    elif method == "static":
        # convert percentage into [0,1]
        treshold = threshold / 100.
        
        # threshold image
        img_binary = enhanced_img < threshold
        
        # perform morphological closing to fill gaps in particules
        img_binary = skimage.morphology.binary_closing(img_binary, np.ones((adapt_closing, adapt_closing)))
        
        
    elif method == "auto":
        # compute distribution of grey levels
        img_small = skimage.transform.rescale(img, 0.2, multichannel=False, anti_aliasing=False)
    
        # keep only central band of the small image by removing 1/4th of lines at the top and 1/4th of lines at the bottom
        img_center = img_small[round(img_small.shape[0]/4):round(3*img_small.shape[0]/4),:]
        # compute grey level variance on centered small version of non enhanced image
        var = img_center.var()
        
        # make small version of enhanced image to compute thresholds
        en_img_small = skimage.transform.rescale(enhanced_img, 0.2, multichannel=False, anti_aliasing=False)
    
        # If var higher than method_threshold, use adaptative thresholding
        if var > auto_threshold:
            # define the new threshold based on percentile
            threshold = np.percentile(en_img_small, (threshold))
            # threshold image
            img_binary = enhanced_img < threshold
            # pixels darker than threshold are True, others are False
        
            # perform morphological closing to fill gaps in particules
            img_binary = skimage.morphology.binary_closing(img_binary, np.ones((adapt_closing, adapt_closing)))

        
        # If var lower than method_threshold, use Otsu thresholding
        else:
            # threshold image
            img_binary = img < skimage.filters.threshold_otsu(en_img_small)
            
            # perform morphological closing to fill gaps in particules
            #img_binary = skimage.morphology.binary_closing(img_binary, np.ones((otsu_closing, otsu_closing)))
            
            
            ## define the new threshold based on percentile
            #threshold = np.percentile(en_img_small, (threshold))
            ## threshold image
            #img_binary = enhanced_img < threshold
            ## pixels darker than threshold are True, others are False
            #
            ## perform morphological closing to fill gaps in particules
            #img_binary = skimage.morphology.binary_closing(img_binary, np.ones((adapt_closing, adapt_closing)))
        
    else:
        raise ValueError("unknown `method` argument")

    # label (i.e. find connected components of) particles and number them
    img_labelled = skimage.measure.label(img_binary, background=False, connectivity=2)
    
    # keep only large particles
    
    # # erase small regions from the labelled image
    # regions = skimage.measure.regionprops(img_labelled)
    # small_regions = [x for x in regions if fast_particle_area(x) < min_area]
    # img_labelled_large = img_labelled
    # for r in small_regions:
    #     img_labelled_large[r._slice] = img_labelled_large[r._slice] * (img_labelled_large[r._slice] != r.label)

    # recreate a labelled images wiht only large regions
    regions = skimage.measure.regionprops(img_labelled)
    large_regions = [r for r in regions if fast_particle_area(r) > min_area]
    img_labelled_large = np.zeros_like(img_labelled)
    for r in large_regions:
        img_labelled_large[r._slice] = (img_labelled[r._slice] == r.label) * r.label
    
    return(img_labelled_large)

 
def fast_particle_area(x):
    return(np.sum(x._label_image[x._slice] == x.label))
