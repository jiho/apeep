import logging

import skimage.transform
import skimage.exposure
import numpy as np

import apeep.timers as t

# from ipdb import set_trace as db

@t.timer
def enhance(img, cfg):
    """
    Enhance (improve contrast of) flat-fielded image
    
    Args:
        img (ndarray): flat-fielded image (of type float)
        cfg (dict): configuration options
    
    Returns:
        ndarray: enhanced image (of type float)
        ndarray: downscaled enhanced image (of type float)
    """
    # get general logger
    log = logging.getLogger()
    
    ## Rescale max/min intensity ----
    # compute distribution of grey levels
    img_small = skimage.transform.rescale(img, 0.2, multichannel=False, anti_aliasing=False)
    # NB: much faster without antialiasing and should be OK for percentile comparison
    # rescale intensity based on these percentiles
    dark_limit, light_limit = np.percentile(img_small, (cfg['enhance']['dark_threshold'],cfg['enhance']['light_threshold']))
    img_eq = skimage.exposure.rescale_intensity(img, in_range=(dark_limit, light_limit))
    
    ## Reshape histogram ----
    # maxv = img.max()
    # minv = img.min()
    # img_eq = (img - minv) / (maxv - minv)
    # img_eq = exposure.equalize_adapthist(img_eq, clip_limit=0.001)
    
    # import seaborn as sns
    # from matplotlib import pyplot as plt    
    # sns.distplot(img.flatten(), kde=False, bins=20)
    # sns.distplot(img_eq.flatten(), kde=False, bins=20)
    # plt.show()
    
    return(img_eq, img_small)
