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
img = cv2.imread('../out/full/20130726232035_235964.png')[:,:,1]
imgthr = np.where(img < 240, 0. , 1. )
imglabelled = measure.label(imgthr, background=1.)

# measure properties (in a function to be able to repeat it and get a fresh properties variable for each test)
def envir(img, imglabelled):
    prop = measure.regionprops(label_image=imglabelled, intensity_image=img)
    len(prop)
    return(prop)
#

# select a criterion to filter particles by
min_area = 300


## List comprehension -----------------------------------------------------

prop = envir(img, imglabelled)
s = t.b()
prop_s = [x for x in prop if x['area'] > min_area]
for c_prop in prop_s:
    a = 1 + 1

print 'list comp + [] :', t.e(s)

prop = envir(img, imglabelled)
s = t.b()
prop_s = [x for x in prop if x.area > min_area]
for c_prop in prop_s:
    a = 1 + 1

print 'list comp + .:', t.e(s)

prop = envir(img, imglabelled)
s = t.b()
prop_s = [x for x in prop if iu.get_particle_area(x) > min_area]
for c_prop in prop_s:
    a = 1 + 1

print 'list comp + direct access:', t.e(s)


## Filter -----------------------------------------------------------------
prop = envir(img, imglabelled)

s = t.b()
prop_s = filter(lambda x: x.area > min_area, prop)
for c_prop in prop_s:
    a = 1 + 1

print 'filter + lambda:', t.e(s)


prop = envir(img, imglabelled)

def my_filter(x, crit=min_area):
    return(x.area > crit)

s = t.b()
prop_s = filter(my_filter, prop)
for c_prop in prop_s:
    a = 1 + 1

print 'filter + predefined function:', t.e(s)

prop = envir(img, imglabelled)

def my_filter(x, crit=min_area):
    return(iu.get_particle_area(x) > crit)

s = t.b()
prop_s = filter(my_filter, prop)
for c_prop in prop_s:
    a = 1 + 1

print 'filter + direct access:', t.e(s)


## Generator --------------------------------------------------------------

prop = envir(img, imglabelled)

def filter_by_area(x, crit):
    for el in x:
        if el['area'] > crit: yield el

s = t.b()
for c_prop in filter_by_area(prop, crit=min_area):
    a = 1 + 1

print 'generator + []:', t.e(s)


prop = envir(img, imglabelled)

def filter_by_area(x, crit):
    for el in x:
        if el.area > crit: yield el

s = t.b()
for c_prop in filter_by_area(prop, crit=min_area):
    a = 1 + 1

print 'generator + . :', t.e(s)


prop = envir(img, imglabelled)

def filter_by_area(x, crit):
    for el in x:
        if iu.get_particle_area(el) > crit: yield el

s = t.b()
for c_prop in filter_by_area(prop, crit=min_area):
    a = 1 + 1

print 'generator + direct access :', t.e(s)


