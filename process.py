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
output_size = 5     # in nb of frames
top = 'right'
scan_per_s = 28000


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
# from skimage import exposure

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


# initialise moving window
cap = cv2.VideoCapture(all_avi[0])
# # get dimensions from `cap` properties
# img_width = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH))
# img_height = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))
# # and create a black moving window
# window = np.zeros((window_size, img_width), dtype=np.uint8)
# read first frame
return_code, img = cap.read()
if not return_code:
    sys.exit('error initialising moving window for averaging')
cap.release()
# convert it to grey scale
img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
# extract dimensions
dims = img.shape
img_height = dims[0]
img_width  = dims[1]
# cut the appropriate part of the image to initialise the moving window
window = img[range(0,window_size),]
log.info('frame dimensions height x width : ' + str(img_height) + ' x ' + str(img_width) )


# initialise output image
output_size = output_size * img_height
output = np.zeros((output_size, img_width))
# output.shape
# output.dtype


# information messages
if debug() :
    cv2.imwrite('window.png', window)
    cv2.imwrite('output.png', output)

log.info('initialised data containers:')
log.info('  moving average window: ' + str(window.shape))
log.info('  output image: ' + str(output.shape))


## Loop over avi files ----------------------------------------------------

# index of lines of pixels in the
i_w = 0     # moving window
i_o = 0     # output buffer
if debug() :
    line_counter = 1

for i_avi in range(0,len(all_avi)) :

    avi_file = all_avi[i_avi]

    # open avi file
    log.info('open file ' + avi_file)
    cap = cv2.VideoCapture(avi_file)

    # parse the start time of the current avi file from its name
    time_now = datetime.strptime(all_avi[i_avi], input_dir + '/%Y%m%d%H%M%S.%f.avi')

    # compute time step for each frame or each scanned line
    line_step = 1. / scan_per_s
    frame_step = line_step * img_height
    # convert to time spans
    line_step = timedelta(seconds=line_step)
    frame_step = timedelta(seconds=frame_step)
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
        # log.debug('frame read')

        # check the frame was read correctly
        # if not exit the loop on this file to jump to the next
        if not return_code :
            log.info('termination of file ' + avi_file)
            break

        # convert to gray scale
        # img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img = img[:,:,1]
        # log.debug('frame converted to grayscale')
        # cv2.imshow('frame', img)

        # convert to floating point (for mean, division, etc.)
        img = img * 1.0
        # log.debug('frame converted to float')
        # img.dtype
        # cv2.imshow('frame', img)

        # loop over scanned lines in that frame
        for i_l in range(0, img_height):
            # if debug() :
            #     log.debug('process line nb ' + str(line_counter))
            #     print 'process line nb ' + str(line_counter)
            #     line_counter += 1

            current_line = img[i_l,]

            # add the line to the moving window
            window[i_w,] = current_line
            # cv2.imshow('window', window)

            # compute mean per column
            m = np.mean(window, 0)
            # TODO check if removing the contribution of the old line and adding the new line is faster

            # compute flat field = divide by mean
            output[i_o,] = current_line / m

            # shift the indexes of the moving window
            i_w += 1
            if i_w == window_size :
                i_w = 0
                # log.debug('loop over moving window')

            # and of the output buffer
            i_o += 1
            # act on the image when it is complete
            if i_o == output_size :
                i_o = 0

                # compute filename based on time
                time_end = time_now + frame_step * i_f + line_step * i_l
                time_start = time_end - line_step * output_size

                output_file_name = datetime.strftime(time_start, '%Y%m%d%H%M%S_%f.png')
                output_file_name = os.path.join(output_dir, output_file_name)
                log.debug('output processed image to: ' + output_file_name)

                # prepare the output image
                # rescale to [0,1]
                output = output - output.min()
                output = output / output.max()

                # reconvert to 8-bit grey level
                output = (output * 255.0)

                # rotate to account for the orientation
                if top == 'right' :
                    output_rotated = np.flipud(output.T)
                elif top == 'left' :
                    output_rotated = np.fliplr(output.T)
                    # TODO check that this keeps the direction of motion from left to right in the final image

                # output the file
                # cv2.imwrite(output_file_name, output_rotated.astype('uint8'))
                cv2.imwrite(output_file_name, output_rotated)
                # NB: apparently, the conversion to int is not necessary for imwrite
                #     it is for imshow
                # cv2.imshow('output', output_rotated.astype('uint8'))



        # increment frame counter
        i_f += 1

    # finished reading the frames, close the avi file
    log.info('close file ' + avi_file)
    cap.release()

# # Contrast stretching
# TODO try to cleanup the background by moving light greys towards white
# p1, p2 = np.percentile(img, (0.01, 99.99))
# img_exp = exposure.rescale_intensity(img, in_range=(p1, p2))
# cv2.imshow('frame', img_exp)
# cv2.imshow('frame', img)

log.info('---END---')
