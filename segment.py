#!/usr/bin/env python2

import hashlib
import os

import numpy as np
import cv2
# from skimage.io import imread
# from skimage.transform import resize
from skimage import measure
from skimage import morphology

from img import view    # interactive image plot
import timers as t      # simple timers for profiling

def segment(img, log, threshold=150, dilate=4, min_area=300, pad=4, return_mask=False):
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

    # add padding outside the original image with white to make sure we can extract particles on the border
    # NB: padding should take in account, the amount of padding in the particles images AND the amount of dilation of particles (because a black dot on the border would be dilated)
    s = t.b()
    img_padding = pad + dilate
    if (pad + dilate) > 0 :
        dims = img.shape
        # horizontal array to pad top and bottom
        hpad = np.ones((img_padding, dims[1])) * 255
        hpad = hpad.astype('uint8')
        # vertical array to pad left and right
        vpad = np.ones((dims[0]+2*img_padding, img_padding)) * 255
        vpad = vpad.astype('uint8')
        # pad original image
        imgpadded = np.concatenate((hpad, img, hpad))
        imgpadded = np.concatenate((vpad, imgpadded, vpad), 1)
    else :
        imgpadded = img
    # view(imgpadded)
    log.debug('segment: image padded' + t.e(s))

    # threshold image, make particles black
    s = t.b()
    #           where(condition            , true value, false value)
    imgthr = np.where(imgpadded < threshold, 0.        , 1.         ) 
    # view(imgthr)
    log.debug('segment: image thresholded' + t.e(s))
    
    # dilate particles, to consider what may be around the thresholded regions
    s = t.b()
    imgdilated = morphology.binary_erosion(imgthr, np.ones((dilate, dilate)))
    # view(imgdilated)
    log.debug('segment: image dilated' + t.e(s))
    

    # label (i.e. give a sequential number to) particles
    s = t.b()
    imglabelled = measure.label(imgdilated, background=1.)
    # view(imglabelled)
    log.debug('segment: image labelled' + t.e(s))

    # measure particles
    s = t.b()
    particles_properties = measure.regionprops(label_image=imglabelled, intensity_image=imgpadded)
    n_part = len(particles_properties)
    log.debug('segment: ' + str(n_part) + ' particles measured' + t.e(s))

    # keep only large ones
    s = t.b()
    particles_properties = [x for x in particles_properties if x['area'] > min_area]
    # TODO this is long, look into how to make it faster
    n_part = len(particles_properties)
    log.debug('segment: ' + str(n_part) + ' large particles selected' + t.e(s))
    
    # compute mask for large particles
    if return_mask :
        s = t.b()
        # get labels of large particles
        labels = [x.label for x in particles_properties]

        # prepare storage for the masks for each particle = n_particles repetitions of the image array
        dims = imglabelled.shape
        large_particle_masks = np.ndarray(shape=(dims[0], dims[1], n_part), dtype=bool)

        # compute the mask for each particle
        for i in range(n_part):
            large_particle_masks[:,:,i] = (imglabelled == labels[i])
        # compute the total mask (1=particle, 0=background)
        large_particle_mask = np.sum(large_particle_masks, 2)
        log.debug('segment: particles mask computed' + t.e(s))
    
    # for each particle:
    # - construct an image of the particle over blank space
    # - extract the measurements of interest
    # save them in
    particles = []
    
    s = t.b()
    for x in particles_properties :
        
        # extract the particle (with padding) and its mask
        x_start = x.bbox[0] - pad
        x_stop  = x.bbox[2] + pad
        y_start = x.bbox[1] - pad
        y_stop  = x.bbox[3] + pad
        particle = imgpadded[x_start:x_stop, y_start:y_stop]
        particle_mask = imglabelled[x_start:x_stop, y_start:y_stop]
        # blank out the pixels outside the particle
        particle = np.where(particle_mask == x.label, particle, 255)
        # TODO make sure we are not editing the actual image here
        # view(particle, False)
        # log.debug('segment: particle ' + str(x.label) + ': background masked')
        
        # s = t.b()
        # make of a copy of the array in memory to be able to compute its md5 digest
        # particle = np.copy(particle, order='C')
        # print particle.shape
        # TODO check if that is necessary
        # view(particle, False)
        
        particles = particles + [particle]
        # log.debug('segment: particle ' + str(x.label) + ': particle extracted')
    
        # TODO cf x.orientation for rotation and aligning images with skimage.rotate
    log.debug('segment: ' + str(len(particles)) + ' particles extracted' + t.e(s))
    
    if return_mask:
        return (particles, particles_properties, large_particle_mask)
    else:
        return (particles, particles_properties)
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
    particles: numpy.ndarray of dtype uint8
        particle images data
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
    ret = cv2.imwrite(file_name, particle)
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

# file_name = 'out/20130723215019_683964.png'
# img = cv2.imread(file_name, cv2.CV_LOAD_IMAGE_GRAYSCALE)
# # im = imread('out/20130723215019_683964.png')
# # view(img)
#
# particles, properties = segment(img)
# print len(particles)
# print len(properties)
# # print len(properties[0])
# # print(dir(properties))
#
# properties_labels = ['area',
#                      'convex_area',
#                      'filled_area',
#                      'eccentricity',
#                      'equivalent_diameter',
#                      'euler_number',
#                      'inertia_tensor_eigvals',
#                      'major_axis_length',
#                      'minor_axis_length',
#                      'max_intensity',
#                      'mean_intensity',
#                      'min_intensity',
#                      'moments_hu',
#                      'weighted_moments_hu',
#                      'perimeter',
#                      'orientation',
#                      'centroid']
#
# properties_names = extract_properties_names(properties[0], properties_labels)
# print properties_names
#
# properties = [extract_properties(x, properties_labels) for x in properties]
# print len(properties)
# print len(properties[0])
#
#
# md5 = [write_particle_image(x, 'particles') for x in particles]
#
# import csv
# csv_file = 'particles/particles.csv'
# csv_handle = open(csv_file, 'wb')
# csv_writer = csv.writer(csv_handle)
# csv_writer.writerow(properties_names)
# csv_writer.writerows(properties)
# csv_handle.close()
#
#
#
#
