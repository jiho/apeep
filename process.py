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

input_dir = '.'
output_dir = '.'
window_size = 300   # in px
output_size = 500   # in px
top = 'right'


## Setup ------------------------------------------------------------------

import numpy as np
import logging as log
import cv2 as cv2
import glob
from datetime import datetime, timedelta
import sys
# from skimage import exposure


# set log
log_file = output_dir + '/process_log.txt'
# TODO add current time to the name
log.basicConfig (
    level=log.DEBUG,
    format='%(asctime)s : %(levelname)s : %(message)s',
    filename=log_file,
    filemode = 'w',
)

def debug():
    """detect if log level is DEBUG"""
    return log.getLogger().isEnabledFor(log.DEBUG)


## Initialisation ---------------------------------------------------------

# list available avi files
log.info('looking for avi files in : ' + input_dir)
all_avi = glob.glob(input_dir + '/*.avi')

n_avi = len(all_avi)
log.info('detected ' + str(n_avi) + ' avi files')


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

for i_avi in range(0,len(all_avi)-1) :
    # NB: we stop on file before the end to be able to compute framerate
    # TODO change this and assume the frame rate did not change

    avi_file = all_avi[i_avi]

    # open avi file
    log.info('open file ' + avi_file)
    cap = cv2.VideoCapture(avi_file)

    # compute sampling frequency

    # number of frames
    n_frames = int(round(cap.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))) + 1
    # NB: frame count should be 430. This gives 429, assuming the first is number 0
    log.info('  file has ' + str(n_frames) + ' frames')

    # time between this and the next file
    time_now = datetime.strptime(all_avi[i_avi], './%Y%m%d%H%M%S.%f.avi')
    time_next = datetime.strptime(all_avi[i_avi+1], './%Y%m%d%H%M%S.%f.avi')

    # compute time step for each frame or each scanned line
    # for 2 successive avi files with n_frames = 3
    # file     : 1     2   ...
    # frames   : 1 2 3 1 2 ...
    # intervals:  1 2 3    ...
    frame_step = (time_next - time_now).total_seconds() / n_frames
    line_step = frame_step / img_height
    log.info('  time step for one frame is ' + \
               str(round(frame_step, ndigits=5)) + ' s')
    # convert to time spans
    frame_step = timedelta(seconds=frame_step)
    line_step = timedelta(seconds=line_step)


    # loop over frames of that file
    for i_f in range(0, n_frames):

        # read a frame
        log.debug('read frame nb ' + str(i_f+1))
        return_code, img = cap.read()

        # check the frame was read correctly
        # if not exit the loop on this file to jump to the next
        if not return_code :
            log.warning('abnormal termination of file ' + avi_file)
            break

        # convert to gray scale
        # TODO check what happens if we just select the first colour channel
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # cv2.imshow('frame', img)

        # convert to floating point (for mean, division, etc.)
        img = img * 1.0
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


    # finished reading the frames, close the avi file
    cap.release()
    log.info('close file ' + avi_file)

# # Contrast stretching
# p1, p2 = np.percentile(img, (0.01, 99.99))
# img_exp = exposure.rescale_intensity(img, in_range=(p1, p2))
# cv2.imshow('frame', img_exp)
# cv2.imshow('frame', img)
