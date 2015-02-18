#!/usr/bin/env python2

import os
import sys

import cv2
import numpy as np
from skimage import measure

sys.path.append(os.path.abspath('..'))  # allows to add times to path
import timers as t
import image_utils as iu

# set and extract particles from a sample image
img = cv2.imread('../20130726233552_560756.png')[:,:,1]
imgthr = np.where(img < 100, 0. , 1. ) 
imglabelled = measure.label(imgthr, background=1.)

# measure properties (in a function to be able to repeat it and get a fresh properties variable for each test)
def envir(img, imglabelled):
    prop = measure.regionprops(label_image=imglabelled, intensity_image=img)
    len(prop)
    return(prop)
#

# create a function that does some stuff with the particles
def get_particle(x, img, imglabelled) :
    x_start = x.bbox[0]
    x_stop  = x.bbox[2]
    y_start = x.bbox[1]
    y_stop  = x.bbox[3]
    particle = img[x_start:x_stop, y_start:y_stop]
    # and its mask
    particle_mask = imglabelled[x_start:x_stop, y_start:y_stop]
    # blank out the pixels outside the particle
    particle = np.where(particle_mask == x.label, particle, 1.)
    return(particle)
#

# select a criterion to filter particles by
min_area = 300    


## List comprehension -----------------------------------------------------

prop = envir(img, imglabelled)
s = t.b()
prop_s = [x for x in prop if x['area'] > min_area]
parts = []
for c_prop in prop_s:
    part = get_particle(c_prop, img, imglabelled)
    parts = parts + [part]

print 'list comp + [] :', t.e(s)
len(parts)

prop = envir(img, imglabelled)
s = t.b()
prop_s = [x for x in prop if x.area > min_area]
parts = []
for c_prop in prop_s:
    part = get_particle(c_prop, img, imglabelled)
    parts = parts + [part]

print 'list comp + .:', t.e(s)
len(parts)

prop = envir(img, imglabelled)
s = t.b()
prop_s = [x for x in prop if iu.get_particle_area(x) > min_area]
parts = []
for c_prop in prop_s:
    part = get_particle(c_prop, img, imglabelled)
    parts = parts + [part]

print 'list comp + direct access:', t.e(s)
len(parts)


## Filter -----------------------------------------------------------------
prop = envir(img, imglabelled)

s = t.b()
prop_s = filter(lambda x: x.area > min_area, prop)
parts = []
for c_prop in prop_s:
    part = get_particle(c_prop, img, imglabelled)
    parts = parts + [part]

print 'filter + lambda:', t.e(s)
len(parts)


prop = envir(img, imglabelled)

def my_filter(x, crit=min_area):
    return(x.area > crit)

s = t.b()
prop_s = filter(my_filter, prop)
parts = []
for c_prop in prop_s:
    part = get_particle(c_prop, img, imglabelled)
    parts = parts + [part]

print 'filter + predefined function:', t.e(s)
len(parts)

prop = envir(img, imglabelled)

def my_filter(x, crit=min_area):
    return(iu.get_particle_area(x) > crit)

s = t.b()
prop_s = filter(my_filter, prop)
parts = []
for c_prop in prop_s:
    part = get_particle(c_prop, img, imglabelled)
    parts = parts + [part]

print 'filter + direct access:', t.e(s)
len(parts)


## Generator --------------------------------------------------------------

prop = envir(img, imglabelled)

def filter_by_area(x, crit):
    for el in x:
        if el['area'] > crit: yield el

s = t.b()
parts = []
for c_prop in filter_by_area(prop, crit=min_area):
    part = get_particle(c_prop, img, imglabelled)
    parts = parts + [part]

print 'generator + []:', t.e(s)
len(parts)


prop = envir(img, imglabelled)

def filter_by_area(x, crit):
    for el in x:
        if el.area > crit: yield el

s = t.b()
parts = []
for c_prop in filter_by_area(prop, crit=min_area):
    part = get_particle(c_prop, img, imglabelled)
    parts = parts + [part]

print 'generator + . :', t.e(s)
len(parts)


prop = envir(img, imglabelled)

def filter_by_area(x, crit):
    for el in x:
        if iu.get_particle_area(el) > crit: yield el

s = t.b()
parts = []
for c_prop in filter_by_area(prop, crit=min_area):
    part = get_particle(c_prop, img, imglabelled)
    parts = parts + [part]

print 'generator + direct access :', t.e(s)
len(parts)


