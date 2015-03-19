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

def segment(img, log, threshold_method='percentile', threshold=1.5, dilate=3, min_area=300, pad=4):
    """
    Segment an image into particles
    
    Parameters
    ----------
    img : a 2D numpy.ndarray of float
        a grey scale image from which to extract particles; 0 = black, 1 = white
    threshold_method : string
       either 'percentile' or 'fixed'
    threshold : float (default 1.5)
       if 'threshold_method' is 'percentile', the percentile of dark pixels
       to select; 2 would select the 2% darkest pixels on the image
       if 'threshold_method' is 'fixed' a grey level (0-1); all pixels darker
       than threshold will be considered as part of particles
    dilate : int (default 4)
        after thresholding, particles are "grown" by 'dilate' pixels to include
        surrounding pixels which may be part of the organism but are not dark enough
    min_area : int (default 300)
        particles of area less than 'min_area' (after dilation), in pixels, are
        discarded
    pad : int (default 4)
        padding to add around the particle image, in pixels
    
    Returns
    -------
    particles : list of numpy.ndarray
        a list of particle images
    particles_properties : list of RegionProperties
        a list of list of particles properties (in the same order)
    particles_mask : numpy.ndarray
        the original image with only particles of interest displayed
    """

    # add padding outside the original image with white to make sure we can extract particles on the border
    # NB: padding should take in account, the amount of padding in the particles images AND the amount of dilation of particles (because a black dot on the border would be dilated)
    s = t.b()
    img_padding = pad + dilate
    dims = img.shape
    if (pad + dilate) > 0 :
        # horizontal array to pad top and bottom
        hpad = np.ones((img_padding, dims[1]))
        # vertical array to pad left and right
        vpad = np.ones((dims[0]+2*img_padding, img_padding))
        # pad original image
        imgpadded = np.concatenate((hpad, img, hpad))
        imgpadded = np.concatenate((vpad, imgpadded, vpad), 1)
    else :
        imgpadded = img
    # iu.view(imgpadded)
    log.debug('segment: image padded' + t.e(s))

    # threshold image, make particles black
    # find threshold level
    s = t.b()
    if threshold_method == 'percentile' :
        # rescale image to a smaller size to compute percentiles faster
        img_small = rescale(img, 0.2)
        threshold = np.percentile(img_small, threshold)
        # NB: a scale factor of 0.2 seems to be a good compromise between enhanced speed and representativity of the original image
        # TODO add bounds to the threshold to avoid being thrown off by large black stuff
    elif threshold_method == 'fixed' :
        treshold = treshold
        # TODO check threshold is in [0,1]
    else :
        log.error('Unknown threshold_method : ' + threshold_method)
    log.debug('segment: threshold level computed at ' + str(threshold) + t.e(s))
    # actually threshold the image
    s = t.b()
    #           where(condition            , true value, false value)
    imgthr = np.where(imgpadded < threshold, 0.        , 1.         ) 
    # iu.view(imgthr)
    log.debug('segment: image thresholded' + t.e(s))
    
    # dilate particles, to consider what may be around the thresholded regions
    s = t.b()
    if dilate >= 1 :
        imgdilated = morphology.binary_erosion(imgthr, np.ones((dilate, dilate)))
    else :
        imgdilated = imgthr
    # iu.view(imgdilated)
    log.debug('segment: image dilated' + t.e(s))
    
    # label (i.e. give a sequential number to) particles
    s = t.b()
    imglabelled = measure.label(imgdilated, background=1.) + 1
    # TODO remove the +1 here with skimage 0.12
    # added 1 here because
    # - background is labelled -1 and particles are labelled starting at 0
    # - regionprops ignores values <= 0, so it ignores the first particle
    # iu.view(imglabelled)
    log.debug('segment: image labelled' + t.e(s))
    
    # measure particles
    s = t.b()
    particles_properties = measure.regionprops(label_image=imglabelled, intensity_image=imgpadded)
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
    particles_mask = np.ones_like(imglabelled, dtype=int)
    
    s = t.b()
    for x in particles_properties :
        
        # extract the particle (with padding)
        x_start = x.bbox[0] - pad
        x_stop  = x.bbox[2] + pad
        y_start = x.bbox[1] - pad
        y_stop  = x.bbox[3] + pad
        # TODO use x._slice?
        particle = imgpadded[x_start:x_stop, y_start:y_stop]
        # and its mask
        particle_mask = imglabelled[x_start:x_stop, y_start:y_stop]
        # blank out the pixels outside the particle
        particle = np.where(particle_mask == x.label, particle, 1.)
        # iu.view(particle, False)
        # log.debug('segment: particle ' + str(x.label) + ': background masked')
        
        # put the mask in the full image mask
        particles_mask[x_start:x_stop, y_start:y_stop] = np.where(particle_mask == x.label, 0., particles_mask[x_start:x_stop, y_start:y_stop])
        
        particles = particles + [particle]
        # log.debug('segment: particle ' + str(x.label) + ': particle extracted')
        
        # TODO cf x.orientation for rotation and aligning images with skimage.rotate
    # remove padding from the mask
    particles_mask = particles_mask[img_padding:(img_padding+dims[0]),img_padding:(img_padding+dims[1])]
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
# from img import view    # interactive image plot
#
# log = logging.getLogger('my_log')
# logging.basicConfig(
#     level=logging.DEBUG,
#     stream=sys.stdout,
#     format='%(asctime)s : %(levelname)s : %(message)s',
# )
#
# file_name = 'tests/concave_particle.png'
# img = cv2.imread(file_name, cv2.CV_LOAD_IMAGE_GRAYSCALE)
# view(img)
# particles, properties, mask = segment(img, log, min_area=10, dilate=0)
# cv2.imwrite('mask.png', mask*255)
# for particle in particles:
#     write_particle_image(particle, 'out', log)
