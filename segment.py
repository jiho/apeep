#!/usr/bin/env python2

# import logging as log
import hashlib
import os
import logging as log

import numpy as np
import cv2
# from skimage.io import imread
# from skimage.transform import resize
from skimage import measure
from skimage import morphology

from img import view    # interactive image plot
import timers as t      # simple timers for profiling

def segment(img, threshold=150, dilate=4, min_area=300, pad=4):
    """
    Segment an image into particles
    
    Parameters
    ----------
    img : a 2D numpy.ndarray of dtype uint8
        an 8-bit grey scale image from which to extract particles
    threshold : int (default 150)
       a grey level (0-255); all pixels darker than threshold will be considered
       as part of particles
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
    """

    # pad original image with white to make sure we can extract particles on the border
    s = t.b()
    if pad > 0 :
        dims = img.shape
        # horizontal array to pad top and bottom
        hpad = np.ones((pad, dims[1])) * 255
        hpad = hpad.astype('uint8')
        # vertical array to pad left and right
        vpad = np.ones((dims[0]+2*pad, pad)) * 255
        vpad = vpad.astype('uint8')
        # pad original image
        imgpadded = np.concatenate((hpad, img, hpad))
        imgpadded = np.concatenate((vpad, imgpadded, vpad), 1)
    else :
        imgpadded = img
    # view(imgpadded)
    log.debug('segment: image padded')
    t.e(s, 'pad')

    # threshold image, make particles black
    s = t.b()
    #           where(condition            , true value, false value)
    imgthr = np.where(imgpadded < threshold, 0.        , 1.         ) 
    # view(imgthr)
    t.e(s, 'threshold')
    # log.debug('segment: image thresholded')
    
    # dilate particles, to consider what may be around the thresholded regions
    s = t.b()
    imgdilated = morphology.binary_erosion(imgthr, np.ones((dilate, dilate)))
    # view(imgdilated)
    t.e(s, 'dilate')
    # log.debug('segment: image dilated')
    

    # label (i.e. give a sequential number to) particles
    s = t.b()
    imglabelled = measure.label(imgdilated, background=1.)
    # view(imglabelled)
    t.e(s, 'label')
    # log.debug('segment: image labelled')

    # measure particles
    s = t.b()
    particles_properties = measure.regionprops(label_image=imglabelled, intensity_image=imgpadded)
    t.e(s, 'measure particles')
    # log.debug('segment: particles measured')

    # keep only large ones
    s = t.b()
    particles_properties = [x for x in particles_properties if x['area'] > min_area]
    # TODO this is long, look into how to make it faster
    # len(particles_properties)
    t.e(s, 'select large particles')
    # log.debug('segment: large particles selected')
    

    # for each particle:
    # - construct an image of the particle over blank space
    # - extract the measurements of interest
    # save them in
    particles = []
    
    for x in particles_properties :
        
        s = t.b()
        # extract the particle (with padding) and its mask
        x_start = x.bbox[0] - pad
        x_stop  = x.bbox[2] + pad
        y_start = x.bbox[1] - pad
        y_stop  = x.bbox[3] + pad
        particle = imgpadded[x_start:x_stop, y_start:y_stop]
        particle_mask = imglabelled[x_start:x_stop, y_start:y_stop]
        # blank out the pixels outside the particle
        particle = np.where(particle_mask == x.label, particle, 255)
        # imgmasked = np.where(imglabelled == x.label, imgpadded, 255)
        t.e(s, 'mask outside particle')
        # log.debug('segment: particle ' + str(x.label) + ': background masked')
        
        s = t.b()
        # make of a copy of the array in memory to be able to compute its md5 digest
        particle = np.copy(particle, order='C')
        # TODO check if that is necessary
        # view(particle)
        particles = particles + [particle]
        t.e(s, 'extract particle')
        # log.debug('segment: particle ' + str(x.label) + ': particle extracted')
    
        # TODO cf x.orientation for rotation and aligning images with skimage.rotate
    
    return particles, particles_properties
#


def extract_properties(particle_properties, names) :
    """
    Extract and flatten particles properties
    
    Parameters
    ----------
    particle_properties : list of RegionProperties
        list of particles properties lists, returned by skimage.measure.regionprops;
        one element per particle
    names : list of strings
        names of properties to extract
    
    Returns
    -------
    props : list of lists
        selected particles properties with multi-element properties flattened;
        one element per particle
    """
    props = []
    
    # loop over particles
    for particle in particle_properties:
        particle_props = []
        
        # select properties of interest for this particle
        for name in names:
            prop = prop_list[name]
            
            # if the property has several elements, flatten it
            if isinstance(prop, (tuple, np.ndarray)) :
                expanded_prop = [el for el in prop]
                particle_props = props + expanded_prop
                # TODO considered expanding the names (foo -> foo1, foo2) here but consider performance concerns in doing so for every particle
            else:
                particle_props = props + [prop]
        
        props = props + element_props
    
    return props



