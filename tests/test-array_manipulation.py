#!/usr/bin/env python2

import numpy as np 
import timer


## Test array rotation
# similar to image rotation

a = np.array([[1,2,3], [4, 5, 6], [7, 8, 9.]])
a

np.flipud(a.T)

np.fliplr(a.T)

from skimage import transform
transform.rotate(a, 90)



## Test computation over margins

a = np.array([[1,2,3], [4, 5, 6], [7, 8, 9.]])
a

# mean
x = a.mean(0)
x
x.dtype
a.dtype
a / x
a - x

x = a.mean(1)
(a.T / x).T

# extraction
b = a[range(0,2),2]
b



## Test computation with ints

import numpy as np

a = np.array([[1,2,3], [4, 5, 6], [7, 8, 9]], dtype='uint8')

a - (a + 1)
# rolls back to 255

# convert to float
af = a * 1.0
af - (af + 1)
af - (a + 1)
# works

# convert to signed int
ai = a.astype(int)
ai.dtype
ai - (ai + 1)
# works



## Test casting speed

import numpy as np

a = np.random.uniform(low=0, high=100, size=(10000,10000)).astype('uint8')
a.dtype

@timer.timer
def f(a): af = a * 1.0

f(a)

@timer.timer
def f(a): af = a.astype(float)

f(a)

@timer.timer
def f(a): af = a.astype(np.float16)

f(a)

# all float are quite long. np.float16 is slightly longer

@timer.timer
def f(a): af = a.astype(int)

f(a)

@timer.timer
def f(a): af = a.astype(np.int16)

f(a)

@timer.timer
def f(a): a = a.astype(np.int16, copy=False)

f(a)
# int16 is faster, copy=True or False does not change anything



## Test type casting in computation

a = np.array([1,2,3], dtype='int16')
b = np.array([2,1,4], dtype='int16')
a.dtype

c = ( a - b )
c.dtype

c = ( a - b ) /  1
c.dtype

c = ( a - b ) /  1.0
c.dtype
