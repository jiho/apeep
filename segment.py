#!/usr/bin/env python2

import hashlib
import os

import numpy as np
import cv2
# from skimage.io import imread
# from skimage.transform import resize
from skimage import measure
from skimage import morphology
from skimage.transform import rescale

import image_utils as iu   # image plot, mask creation, ...
import timers as t         # timers for simple profiling

def segment(img, log, threshold=0.1, dilate=3, min_area=300):
    """
    Segment an image into particles
    
    Parameters
    ----------
    img : a 2D numpy.ndarray of float
        a grey scale image from which to extract particles; 0 = black, 1 = white
    threshold : float (default 0.1)
        a grey level (0-1); all pixels darker than threshold will be considered
        as part of particles
    dilate : int (default 4)
        after thresholding, particles are "grown" by 'dilate' pixels to include
        surrounding pixels which may be part of the organism but are not dark enough
    min_area : int (default 300)
        particles of area less than 'min_area' (after dilation), in pixels, are
        discarded
    
    Returns
    -------
    particles : list of numpy.ndarray
        a list of particle images
    particles_properties : list of RegionProperties
        a list of list of particles properties (in the same order)
    particles_mask : numpy.ndarray
        the original image with only particles of interest displayed
    """

    # threshold image
    s = t.b()
    imgthr = img < threshold
    # pixels darker than threshold are True, others are False
    # True is plotted white
    # iu.view(imgthr)
    log.debug('segment: image thresholded' + t.e(s))

    # dilate particles, to consider what may be around the thresholded regions
    s = t.b()
    if dilate >= 1 :
        imgdilated = morphology.binary_dilation(imgthr, np.ones((dilate, dilate)))
        # makes "True" regions larger = dilate particles
    else :
        imgdilated = imgthr
    # iu.view(imgdilated)
    log.debug('segment: image dilated' + t.e(s))
    
    # label (i.e. give a sequential number to) particles
    s = t.b()
    imglabelled = measure.label(imgdilated, background=False, connectivity=2) + 1
    # particles are True, background is False
    # TODO remove the +1 here with skimage 0.12
    # added 1 here because
    # - background is labelled -1 and particles are labelled starting at 0
    # - regionprops ignores values <= 0, so it ignores the first particle
    # iu.view(imglabelled)
    log.debug('segment: image labelled' + t.e(s))
    
    # measure particles
    s = t.b()
    particles_properties = measure.regionprops(label_image=imglabelled, intensity_image=img)
    n_part = len(particles_properties)
    log.debug('segment: ' + str(n_part) + ' particles measured' + t.e(s))
    
    # keep only large particles
    s = t.b()
    particles_properties = [x for x in particles_properties if iu.get_particle_area(x) > min_area]
    n_part = len(particles_properties)
    log.debug('segment: ' + str(n_part) + ' large particles selected' + t.e(s))
    
    # for each particle:
    # - construct an image of the particle over blank space
    # - extract the measurements of interest
    particles = []
    
    # prepare a mask over the whole image on which retained particles will be shown
    particles_mask = np.ones_like(img, dtype=int)
    
    s = t.b()
    for x in particles_properties :
        # extract the particle
        particle = img[x._slice]
        # iu.view(particle, False)
        # and its mask
        particle_mask = imglabelled[x._slice]
        # blank out the pixels outside the particle
        particle = np.where(particle_mask == x.label, particle, 1.)
        # iu.view(particle, False)
        particles = particles + [particle]
        
        # put the mask in the full image mask (to be able to display it and check segmentation)
        particles_mask[x._slice] = np.where(particle_mask == x.label, 0., particles_mask[x._slice])
        
        # TODO cf x.orientation for rotation and aligning images with skimage.rotate
    log.debug('segment: ' + str(len(particles)) + ' particles extracted' + t.e(s))
    
    return (particles, particles_properties, particles_mask)
#

def extract_properties(properties, names) :
    """
    Extract and flatten particles properties
    
    Given a list of properties such as
        [1, (3.2, 1.4), 'foo']
    this function flattens it to
        [1, 3.2, 1.4, 'foo']
    
    Parameters
    ----------
    properties : object of type RegionProperties
        properties of one particle; i.e. one element of the list returned
        by skimage.measure.regionprops
    names : list of strings
        names of properties to extract
    
    Returns
    -------
    props : list
        selected particles properties, with multi-element properties flattened
    """
    extracted_properties = []
        
    # loop over names of properties to extract
    for name in names:
        # extract property
        prop = properties[name]
        # TODO convert pixel based properties into mm
        
        if isinstance(prop, (tuple, np.ndarray)) :
            # if the property has several elements, flatten it
            expanded_prop = [element for element in prop]
            extracted_properties = extracted_properties + expanded_prop
        else:
            extracted_properties = extracted_properties + [prop]

    return extracted_properties
#

def extract_properties_names(properties, names) :
    """
    Create a list of names for flattened particles properties
    
    See 'extract_properties' for extracting and flattening properties
    lists. For a list of properties with names
        ['number', 'coord', 'name']
    this function creates the names for the flattened list
        ['number', 'coord1', 'coord2', 'name']
    
    Parameters
    ----------
    properties : object of type RegionProperties
        properties of one particle; i.e. one element of the list returned
        by skimage.measure.regionprops
    names : list of strings
        names of properties to extract
    
    Returns
    -------
    names : list
        flattened list of properties names
    """
    extracted_names = []
        
    # loop over names of properties to extract
    for name in names:
        # extract property
        prop = properties[name]
        
        if isinstance(prop, (tuple, np.ndarray)) :
            # if the property has several elements, repeat the name and add a numeric suffix
            n = len(prop)
            repeated_name = [name + str(x) for x in range(1,(n+1))]
            extracted_names = extracted_names + repeated_name
        else:
            extracted_names = extracted_names + [name]

    return extracted_names
#

def write_particle_image(particle, output_dir, log) :
    """Write a particle to a file
    
    Parameters
    ----------
    particles: numpy.ndarray of float
        particle images data; 0 = black, 1 = white
    output_dir: string
        directory to write the file in. should exist. is not checked
    
    Returns
    -------
    md5s: string
        md5 digest of the particle, used as file name
    """
    # compute md5 digest which is used as a name
    md5 = hashlib.md5(particle).hexdigest()
    
    # prepare name
    file_name = os.path.join(output_dir, md5 + '.png')
    
    # write image
    # NB: convert to 8-bit integer for writing
    ret = cv2.imwrite(file_name, particle * 255.)
    if not ret:
        log.warning('could not write particle image')

    return(md5)
#

# TODO def save_particles
#   write particles
#   compute time
#   compute properties
#   concatenate all metadata
#   save everything
#
# segment_image
#     segments particles
#     saves particles
#
# segment_images_in_folder
#     read images in a folder
#     compute start time for each image
#     segment_image on each image
#
# import logging
# import cv2
# import sys
# import image_utils as iu
# from skimage.transform import rescale
# import numpy as np
# import timers as t
#
# log = logging.getLogger('my_log')
# logging.basicConfig(
#     level=logging.DEBUG,
#     stream=sys.stdout,
#     format='%(asctime)s : %(levelname)s : %(message)s',
# )
#
# images = ['20130726232035_235964', '20130726233552_560756', '20130726235329_709996']
#
# for scale in [0.05, 0.1, 0.15, 0.2, 0.3] :
#     for percentile in [1, 2] :
#         print ''
#         print 'scale: ', scale, ' percentile: ', percentile
#         for i in images :
#             file_name = i + '.png'
#             img = cv2.imread(file_name, cv2.CV_LOAD_IMAGE_GRAYSCALE)
#             # img.shape
#             # img.dtype
#             img = img / 255.
#             # img.dtype
#
#             s = t.b()
#             thresholdf = np.percentile(img, percentile)
#             # print 'full  :', threshold, t.e(s)
#
#             s = t.b()
#             img_small = rescale(img, scale, mode='constant')
#             thresholds = np.percentile(img_small, percentile)
#             # print 'small :', threshold, t.e(s)
#             print 'diff full - rescaled : ', thresholdf - thresholds
#
# print 'finished'
