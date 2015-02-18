#!/usr/bin/env python2

import numpy as np
import cv2 as cv2
import skimage.io as io

# io.find_available_plugins()
# # io.available_plugins
# {'null': ['imshow', 'imread', 'imsave', 'imread_collection'], 'pil': ['imread', 'imsave', 'imshow', 'imread_collection'], 'qt': ['imshow', 'imsave', 'imread', 'imread_collection'], 'freeimage': ['imread', 'imsave', 'imread_collection'], 'gtk': ['imshow'], 'matplotlib': ['imshow', 'imread', 'imread_collection'], 'test': ['imsave', 'imshow', 'imread', 'imread_collection'], 'simpleitk': ['imread', 'imsave', 'imread_collection'], 'imread': ['imread', 'imsave', 'imread_collection'], 'fits': ['imread', 'imread_collection'], 'tifffile': ['imread', 'imsave', 'imread_collection'], 'gdal': ['imread', 'imread_collection']}
# io.use_plugin('imread')


## Test writing image -----------------------------------------------------

# generate a fake image
img = np.random.randint(0,255,(2048*3,2048))

# save it 20 times
# io.use_plugin('pil')
# io.use_plugin('matplotlib')
for i in range(0,20):
    # cv2.imwrite(str(i) + '.tiff', img)
    # cv2.imwrite(str(i) + '.png', img)
    # cv2.imwrite(str(i) + '.jpg', img)
    # io.imsave(str(i) + '.png', img)

# cv2, 2048x2048
# tiff: 8.5s
# png: 6.5s
# jpg: > 15s

# cv2, 20480x2048
# tiff: 19.386s
# png: 13.807s
# jpg: 36.344s

# -> png wins

# cv2 png vs skimage png, 2048*3,2048
# cv2 4.044s
# pil 24.648s
# matplotlib 24.702s

# -> cv2 wins by a large margin

## Test reading image -----------------------------------------------------

# TODO test skimage.io.imread vs cv2.imread

