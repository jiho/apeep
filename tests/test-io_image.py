#!/usr/bin/env python2

import numpy as np
import cv2 as cv2
import skimage.io as io

img = np.random.randint(0,255,(20480,2048))

for i in range(0,20):
    # cv2.imwrite(str(i) + '.tiff', img)
    cv2.imwrite(str(i) + '.png', img)
    # cv2.imwrite(str(i) + '.jpg', img)

# cv2, 2048x2048
# tiff: 8.5s
# png: 6.5s
# jpg: > 15s

# cv2, 20480x2048
# tiff: 19.386s
# png: 13.807s
# jpg: 36.344s

# -> png wins


# TODO test skimage.io.imwrite
# io.find_available_plugins()
# # io.available_plugins
# io.use_plugin('imread')
# for i in range(0,100):
#     io.imsave(str(i) + '.tiff', img, )

# TODO test skimage.io.imread vs cv2.imread