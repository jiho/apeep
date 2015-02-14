#!/usr/bin/env python2


import numpy as np
import logging as log

from skimage.io import imread
from skimage.transform import resize
from skimage import measure
from skimage import morphology
import cv2

from img import view

import hashlib
import os




from datetime import datetime, timedelta

file_name = 'out/20130723215019_683964.png'
img = cv2.imread(file_name, cv2.CV_LOAD_IMAGE_GRAYSCALE)
# im = imread('out/20130723215019_683964.png')
view(img)

time_start = datetime.strptime(file_name, 'out/%Y%m%d%H%M%S_%f.png')

scan_per_s = 28000
time_step = 1. / scan_per_s
# convert to time spans
time_step = timedelta(seconds=time_step)

output_dir = 'particles'
min_area=300
threshold=150
dilate=4
pad=4

import csv
csv_file = 'particles/particles.csv'
csv_handle = open(csv_file, 'wb')
csv_writer = csv.writer(csv_handle)


properties_labels = ['area',
                     'convex_area',
                     'filled_area',
                     'eccentricity',
                     'equivalent_diameter',
                     'euler_number',
                     'inertia_tensor_eigvals',
                     'major_axis_length',
                     'minor_axis_length',
                     'max_intensity',
                     'mean_intensity',
                     'min_intensity',
                     'moments_hu',
                     'weighted_moments_hu',
                     'perimeter',
                     'orientation',
                     'centroid']
properties_names  = ['name',
                     'date_time',
                     'area',
                     'convex_area',
                     'filled_area',
                     'eccentricity',
                     'equivalent_diameter',
                     'euler_number',
                     'inertia_tensor_eigval1', 'inertia_tensor_eigval2',
                     'major_axis_length',
                     'minor_axis_length',
                     'max_intensity',
                     'mean_intensity',
                     'min_intensity',
                     'moment_hu1', 'moment_hu2', 'moment_hu3', 'moment_hu4', 'moment_hu5', 'moment_hu6', 'moment_hu7',  
                     'weighted_moment_hu1', 'weighted_moment_hu2', 'weighted_moment_hu3', 'weighted_moment_hu4', 'weighted_moment_hu5', 'weighted_moment_hu6', 'weighted_moment_hu7', 
                     'perimeter',
                     'orientation',
                     'centroidx','centroidy']
csv_writer.writerow(properties_names)



def segment(img, time_start, time_step, threshold=150, dilate=4, min_area=300, pad=4):
    """
    Segment an image into particles
    
    Parameters
    ----------
    img : a 2D numpy.ndarray of dtype uint8
        an 8-bit grey scale image from which to extract particles
    time_start : a datetime object
        date and time of the first scan of the image
    time_step : a timedelta object
        the time taken to scan one line of pixels (= 1 divided by the sample rate)
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

    # threshold image, make particles black
    #           where(condition            , true value, false value)
    imgthr = np.where(imgpadded < threshold, 0.        , 1.         ) 
    # view(imgthr)

    # dilate particles, to consider what may be around the thresholded regions
    imgdilated = morphology.binary_erosion(imgthr, np.ones((dilate, dilate)))
    # view(imgdilated)

    # label (i.e. give a sequential number to) particles
    imglabelled = measure.label(imgdilated, background=1.)
    # view(imglabels)

    # measure particles
    particles_properties = measure.regionprops(label_image=imglabelled, intensity_image=imgpadded)

    # keep only large ones
    particles_properties = [x for x in particles_properties if x.area > min_area]
    # TODO check wether it is faster to remove small particles from the mask image and measure with intensity image afterwards
    # len(particles_properties)

    # for each particle:
    # - construct an image of the particle over blank space
    # - extract the measurements of interest
    # save them in
    particles = []
    
    for x in particles_properties :
        # blank out the pixels which are not part of the particle of interest
        imgmasked = np.where(imglabels == x.label, imgpadded, 255)
        # extract the particle (with padding) into a rectangle
        particle = imgmasked[
            (x.bbox[0]-pad):(x.bbox[2]+pad),
            (x.bbox[1]-pad):(x.bbox[3]+pad)]
        # NB: x.bbox = (min_row, min_col, max_row, max_col)
        # make of a copy of the array in memory to be able to compute its md5 digest
        particle = np.copy(particle, order='C')
        # view(particle)
        particles = particles + [particle]
    
        # TODO cf x.orientation for rotation and aligning images with skimage.rotate
    
        # compute md5 digest which is used as a name
        # md5 = hashlib.md5(particle).hexdigest()

        # TODO convert pixel based properties into mm
        #
        # # compute particle capture date and time
        # # start time + number of columns until the centroid * time per column
        # date_time = time_start + int(round(x.centroid[1])) * time_step
        #
        # # add particle name (md5) and date
        # props = [md5, date_time] + props
        #
        # # save to csv
        # csv_writer.writerow(props)
        #
        # compute file name and save image
        # file_name = os.path.join(output_dir, md5 + '.png')
        # ret = cv2.imwrite(file_name, particle)
        # if not ret:
        #     log.warning('could not write particle image')


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



# close csv file
csv_handle.close()
