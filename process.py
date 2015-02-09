#!/usr/bin/env python2
# Should be python3 but getting opencv2 to compile with python3 bindings is complex




## Options ----------------------------------------------------------------
input_dir = '.'
output_dir = '.'
window_size = 300      # in px
output_size = 2048*10  # in px
top = 'right'


## Setup ------------------------------------------------------------------
import numpy as np
import cv2 as cv2
from cv2 import cv as cv
from skimage import exposure
# from matplotlib import pyplot as p
import logging as log
import glob
# from skimage import data, img_as_float
# from scipy import toimage
# import seaborn as sb
from datetime import datetime, timedelta

# set log
log_file='process_log.txt'
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


# get image dimensions from first avi file
cap = cv2.VideoCapture(all_avi[0])
# img_width = int(cap.get(cv.CV_CAP_PROP_FRAME_WIDTH))
# img_height = int(cap.get(cv.CV_CAP_PROP_FRAME_HEIGHT))
ret, img = cap.read()
img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
# TODO check return_code
dims = img.shape
img_height = dims[0]
img_width  = dims[1]
window = img[range(0,window_size),]
window.shape
cap.release()
log.info('frame dimensions height x width : ' + str(img_height) + ' x ' + str(img_width) )


# initialise moving window and image container
# window = np.zeros((window_size, img_width), dtype=np.uint8)
# window.shape
# window.dtype
# TODO initialise the window with actual data form the first avi file
# TODO clean this up
output = np.zeros((output_size, img_width))
# output.shape
# output.dtype
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
    n_frames = int(round(cap.get(cv.CV_CAP_PROP_FRAME_COUNT))) + 1
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

            # compute flat field
            # divide by mean
            output[i_o,] = current_line / m
            
            # shift the indexes of the window and output buffer
            i_w += 1
            i_o += 1
            if i_w == window_size :
                i_w = 0
                # log.debug('loop over moving window')
                

            if i_o == output_size :
                i_o = 0
                
                # base filename based on time
                time_end = time_now + frame_step * i_f + line_step * i_l
                time_start = time_end - line_step * output_size
                
                output_file_name = datetime.strftime(time_start, '%Y%m%d%H%M%S_%f.png')
                # output_file_name = 'output.png'
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
                else :
                    log.error('incorrect \'top\' argument, should be right or left')
                    sys.exit('incorrect \'top\' argument, should be right or left')

                # output the file
                # cv2.imwrite(output_file_name, output_rotated.astype('uint8'))
                cv2.imwrite(output_file_name, output_rotated)
                # NB: apparently, the conversion to int is not necessary for imwrite
                #     it is for imshow
                # cv2.imshow('output', output_rotated.astype('uint8'))


    # finished reading the frames, close the avi file  
    cap.release()
    log.info('close file ' + avi_file)


# gray = cv2.cv2tColor(frame, cv2.COLOR_BGR2GRAY)
#
# cv2.imshow('frame',gray)
# if cv2.waitKey(1) & 0xFF == ord('q'):
#     break

# # Contrast stretching
# p1, p2 = np.percentile(img, (0.01, 99.99))
# img_exp = exposure.rescale_intensity(img, in_range=(p1, p2))
# cv2.imshow('frame', img_exp)
# cv2.imshow('frame', img)
