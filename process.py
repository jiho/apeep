#!/usr/bin/env python2
#
# Search the input directory for avi files
# Consider the avi files as a stream of line scans:
#     open each file
#     read each frame
#     process each line of each frame (from top to bottom)
# On this stream of incoming lines:
#     compute a basic moving average of the grey intensity
#     divide each line by the moving average to remove constant "lines" artefacts
#     store the result in a buffer
#     once the buffer is full
#         post process it
#         save it as an image
#

# TODO swicth to python3 (but getting opencv2 to compile with python3 bindings is complex)


## Options ----------------------------------------------------------------

input_dir = 'in'
output_dir = 'out'
window_size = 1000   # in px
output_size = 10     # in nb of frames
top = 'right'
scan_per_s = 28000
lighten = 0.2


## Setup ------------------------------------------------------------------

import numpy as np
import logging
import cv2 as cv2
import glob
from datetime import datetime, timedelta
import sys
import tempfile
import os
import errno
import time
from skimage import exposure

# setup logging
log_formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s')

log = logging.getLogger('my_log')
log.setLevel(logging.DEBUG)

# setup console log
console_log = logging.StreamHandler()
console_log.setFormatter(log_formatter)
log.addHandler(console_log)

def debug():
    """detect if log level is DEBUG"""
    return logging.getLogger().isEnabledFor(logging.DEBUG)
    # TODO find a better way to do this, like have a debug switch as command line arg

# check options

# check that output directory exists and is writable
if os.path.isdir(output_dir):
    log.debug('output_dir exists')
    # try writing in it
    try:
        ret, tmpname = tempfile.mkstemp(dir=output_dir)
    except:
        log.error('cannot write to output directory')
        raise
    log.debug('output_dir is writable')
    os.remove(tmpname)
else:
    log.info('output directory : \'' + output_dir + '\' does not exist, creating it')
    try:
        os.makedirs(output_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            log.error('cannot create output directory')
            raise
    log.debug('output_dir created')

# once this is OK, create a log file
log_file = os.path.join(output_dir, 'process_log.txt')
# TODO add current time to the name and switch to mode='w'
file_log = logging.FileHandler(log_file)
file_log.setFormatter(log_formatter)
log.addHandler(file_log)

log.info('---START---')

# check input dir
if not os.path.isdir(input_dir):
    log.error('input directory does not exist')
    sys.exit()

# check top orientation
if not top in ('right', 'left') :
    log.error('incorrect \'top\' argument, should be right or left')
    sys.exit()

if ( lighten < 0. ) or ( lighten > 1. ) :
    log.error('lighten should be in [0,1] (0, no change; 1 clip to white)')
    sys.exit()


# check image sizes
if not isinstance(window_size, (int, long, float)) :
    log.error('window_size must be a number')
    sys.exit()

if not isinstance(output_size, (int, long, float)) :
    log.error('output_size must be a number')
    sys.exit()
output_size = int(round(output_size))


## Initialisation ---------------------------------------------------------

# list available avi files
log.info('looking for avi files in : ' + input_dir)
all_avi = glob.glob(input_dir + '/*.avi')

n_avi = len(all_avi)
log.info('detected ' + str(n_avi) + ' avi files')
if n_avi == 0:
    log.error('no avi files to process in ' + input_dir)
    sys.exit()


# initialise moving window with first file
cap = cv2.VideoCapture(all_avi[0])
# read first frame
return_code, img = cap.read()
if not return_code:
    log.error('error reading file ' + all_avi[0] + ' to initialise moving window')
    sys.exit()
cap.release()
# convert it to grey scale (=keep only first channel)
img = img[:,:,1]
# extract dimensions
dims = img.shape
img_height = dims[0]
img_width  = dims[1]
log.info('frame dimensions height x width : ' + str(img_height) + ' x ' + str(img_width) )
if window_size > img_height:
    log.error('window_size should be < ', img_height, ' (less than the size of a frame)')
    sys.exit()
# cut the appropriate part of the image to initialise the moving window
window = img[range(0,window_size),]
window = window.astype(np.int16)
# initialise the column-wise mean
m = np.mean(window, 0)

# create a floating point version of window_size for computation
window_size_f = float(window_size)

# initialise output image
# compute output_size in pixels
output_size = output_size * img_height
# create a blank output image
output = np.zeros((output_size, img_width))

# information messages
if debug() :
    cv2.imwrite('window.png', window)
    cv2.imwrite('output.png', output)

log.info('initialised data containers:')
log.info('  moving average window: ' + str(window.shape))
log.info('  moving average: ' + str(m.shape))
log.info('  output image: ' + str(output.shape))


## Loop over avi files ----------------------------------------------------

# index of lines of pixels in the
i_w = 0     # moving window
i_o = 0     # output buffer
if debug() :
    line_counter = 1

# compute time step for each frame or each scanned line
line_step = 1. / scan_per_s
frame_step = line_step * img_height
# convert to time spans
line_step = timedelta(seconds=line_step)
frame_step = timedelta(seconds=frame_step)

# loop over files
for i_avi in range(0,len(all_avi)) :

    avi_file = all_avi[i_avi]

    # open avi file
    log.info('open file ' + avi_file)
    cap = cv2.VideoCapture(avi_file)

    # parse the start time of the current avi file from its name
    time_now = datetime.strptime(all_avi[i_avi], input_dir + '/%Y%m%d%H%M%S.%f.avi')

    # TODO verify that the computed span is close to this
    # time_next = datetime.strptime(all_avi[i_avi+1], input_dir + '/%Y%m%d%H%M%S.%f.avi')
    # # for 2 successive avi files with n_frames = 3
    # # file     : 1     2   ...
    # # frames   : 1 2 3 1 2 ...
    # # intervals:  1 2 3    ...
    # frame_step = (time_next - time_now).total_seconds() / n_frames
    # line_step = frame_step / img_height
    # log.info('  time step for one frame is ' + \
    #            str(round(frame_step, ndigits=5)) + ' s')

    # loop over frames of that file
    i_f = 0
    while True:

        # read a frame
        log.debug('read frame ' + str(i_f))
        return_code, img = cap.read()
        log.debug('frame read')

        # check the frame was read correctly
        # if not exit the loop on this file to jump to the next
        if not return_code :
            log.info('termination of file ' + avi_file)
            break

        # convert to gray scale
        img = img[:,:,1]
        log.debug('frame converted to grayscale')

        # convert to floating point (for mean, division, etc.)
        img = img.astype(np.int16)
        log.debug('frame converted')
        # cv2.imshow('frame', img)

        # loop over scanned lines in that frame
        for i_l in range(0, img_height):
            # if debug() :
            #     log.debug('process line nb ' + str(line_counter))
            #     print 'process line nb ' + str(line_counter)
            #     line_counter += 1

            # get line scan of interest
            current_line = img[i_l,]

            # update column-wise mean
            m = m + (current_line - window[i_w,]) / window_size_f
            # NB: considerably faster than recomputing the whole mean every time
            #     computing the median is another order of magnitude slower

            # update content of the moving window
            window[i_w,] = current_line

            # compute flat field = divide by mean
            output[i_o,] = current_line / m

            # shift the indexes of the moving window
            i_w += 1
            if i_w == window_size :
                i_w = 0
                log.debug('loop over moving window')

            # and of the output buffer
            i_o += 1
            # act on the image when it is complete
            if i_o == output_size :
                i_o = 0

                # compute filename based on time
                time_end = time_now + (i_f * img_height + i_l) * line_step
                time_start = time_end - line_step * output_size

                output_file_name = datetime.strftime(time_start, '%Y%m%d%H%M%S_%f.png')
                # TODO add end time or sampling freq?
                output_file_name = os.path.join(output_dir, output_file_name)
                log.debug('output processed image to: ' + output_file_name)

                # prepare the output image
                # rescale to [0,1]
                output = output - output.min()
                output = output / output.max()
                log.debug('output image rescaled')

                # stretch contrast
                # p1, p2 = np.percentile(output, (0.01, 99.99))
                # output = exposure.rescale_intensity(output, in_range=(0, 230))
                if lighten > 0.001 :
                    # NB: only lighten when necessary
                    output = exposure.rescale_intensity(output, in_range=(0., 1.-lighten))
                # NB: stretches to [0,1]
                log.debug('output image contrasted')

                # reconvert to 8-bit grey level
                output = (output * 255.0)
                log.debug('output image converted to 8-bit')

                # rotate to account for the orientation
                if top == 'right' :
                    output_rotated = np.flipud(output.T)
                elif top == 'left' :
                    output_rotated = np.fliplr(output.T)
                    # TODO check that this keeps the direction of motion from left to right in the final image
                log.debug('output image rotated')

                # output the file
                # cv2.imshow('output', output_rotated.astype('uint8'))
                # cv2.imwrite(output_file_name, output_rotated.astype('uint8'))
                cv2.imwrite(output_file_name, output_rotated)
                # TODO try to optimise writing of the image which takes ~1.3s for a 10 frames image
                # NB: apparently, the conversion to int is not necessary for imwrite
                #     it is for imshow
                log.debug('output image written to disk')

        # increment frame counter
        i_f += 1

    # finished reading the frames, close the avi file
    cap.release()
    log.debug('closed file ' + avi_file)

# # Contrast stretching
# TODO try to cleanup the background by moving light greys towards white
# p1, p2 = np.percentile(img, (0.01, 99.99))
# img_exp = exposure.rescale_intensity(img, in_range=(p1, p2))
# cv2.imshow('frame', img_exp)
# cv2.imshow('frame', img)

log.info('---END---')
