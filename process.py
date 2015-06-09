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

# TODO switch to python3 (but getting opencv2 to compile with python3 bindings is complex)


## Options ----------------------------------------------------------------

from conf import *

## Setup ------------------------------------------------------------------

import logging
import glob
from datetime import datetime, timedelta
import sys
import os
import csv

import cv2
import numpy as np
from skimage import exposure
from skimage.transform import rescale

import segment
import timers as t
import os_utils as osu
import image_utils as iu


# setup logging
log_formatter = logging.Formatter('%(asctime)s.%(msecs)03d : %(levelname)s : %(message)s', datefmt="%m-%d %H:%M:%S")

log = logging.getLogger('my_log')
if debug :
    log_level = logging.DEBUG
else :
    log_level = logging.INFO
log.setLevel(log_level)

# setup console log
console_log = logging.StreamHandler()
console_log.setFormatter(log_formatter)
log.addHandler(console_log)
# the log will also be saved to a log file in the output directory


# check that output directories exist and are writable
# create them if needed
osu.checkmakedirs(output_dir)
if write_ff_image | write_processed_image | write_mask_image :
    output_dir_full = os.path.join(output_dir, 'full')
    osu.checkmakedirs(output_dir_full)

# once this is OK, create a log file
log_file = os.path.join(output_dir, 'process_log.txt')
# TODO add current time to the name and switch to mode='w'
file_log = logging.FileHandler(log_file)
file_log.setFormatter(log_formatter)
log.addHandler(file_log)


# check options
log.info('---START---')

if detect_particles :
    # initiate csv file to store particles data
    try:
        csv_handle = open(os.path.join(output_dir, 'particles.csv'), 'wb')
    except Exception as e:
        log.error('cannot initiate csv file for particles')
        raise e
    csv_writer = csv.writer(csv_handle)

# check input dir
if not os.path.isdir(input_dir):
    log.error('input directory does not exist')
    sys.exit()

# check top orientation
if not top in ('right', 'left') :
    log.error('incorrect \'top\' argument, should be right or left')
    sys.exit()

# check light_threshold argument
if ( light_threshold < 0. ) or ( light_threshold > 100. ) :
    log.error('light_threshold should be in [0,100] (0, no change; 100, clip to white)')
    sys.exit()

# check image sizes
if not isinstance(window_size, (int, long, float)) :
    log.error('window_size must be a number')
    sys.exit()

if not isinstance(output_size, (int, long, float)) :
    log.error('output_size must be a number')
    sys.exit()
# it is a number of frames = integer
output_size = int(round(output_size))

# TODO check other inputs


## Configuration log ------------------------------------------------------

log.info('CONFIGURATION:')
log.info('input data : ' + input_dir)
log.info('output data : ' + output_dir)
log.info('moving window size (in px) : ' + str(window_size))
log.info('output image size (in number of frames): ' + str(output_size))
log.info('top of image: ' + top)
log.info('scanning rate: ' + str(scan_per_s))
log.info('light_threshold: ' + str(light_threshold))
log.info('dark_threshold: ' + str(dark_threshold))
log.info('dilate: ' + str(dilate))
log.info('min_area: ' + str(min_area))


## Initialisation ---------------------------------------------------------

log.info('INITIALISATION:')

# list available avi files
all_avi = glob.glob(input_dir + '/*.avi')
# sort them in alphanumeric order (glob.glob() does not)
all_avi.sort()
n_avi = len(all_avi)
if n_avi == 0:
    log.error('no avi files to process in ' + input_dir)
    sys.exit()
log.info('found ' + str(n_avi) + ' avi files in \'' + input_dir + '\'')


# get frame dimensions from first file
first_avi = all_avi[0]
cap = cv2.VideoCapture(first_avi)
# read first frame
first_frame = iu.read_grey_frame(cap, log)
if first_frame is None:
    log.error('error reading first frame from ' + first_avi)
    sys.exit()

# extract dimensions
dims = first_frame.shape
img_height = dims[0]
img_width  = dims[1]
log.info('frame dimensions height x width : ' + str(img_height) + ' x ' + str(img_width) )

# initialise moving window
window = first_frame
while window_size > window.shape[0] :
    next_frame = iu.read_grey_frame(cap, log)
    if next_frame is None:
        log.error('error reading frame from file ' + first_avi + ' to initialise moving window')
        sys.exit()
    window = np.vstack((window, next_frame))

# close the video
cap.release()

# cut the appropriate part of the image to initialise the moving window
window = window[range(0,window_size),]
# convert it to int16 because that is what read later
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
if debug :
    cv2.imwrite('window.png', window)
    cv2.imwrite('output.png', output)

log.info('initialised data containers:')
log.info('  moving average window: ' + str(window.shape))
log.info('  moving average: ' + str(m.shape))
log.info('  output image: ' + str(output.shape))


# switch to detect when we are writing the first row of the csv files for particles
first_row = True


# compute time step for each frame or each scanned line
line_step = 1. / scan_per_s
frame_step = line_step * img_height
# convert to time spans
line_step = timedelta(seconds=line_step)
frame_step = timedelta(seconds=frame_step)


## Loop over avi files ----------------------------------------------------

log.info('MAIN LOOP:')

# index of lines of pixels in the
i_w = 0     # moving window
i_o = 0     # output buffer

# loop over files
for i_avi in range(0,len(all_avi)) :

    avi_file = all_avi[i_avi]

    # open avi file
    log.info('open file ' + avi_file)
    # progress report
    log.info('%.2f' % (float(i_avi) / n_avi * 100) + '% complete (' + str(i_avi) + ' / ' + str(n_avi) + ' files)')
    cap = cv2.VideoCapture(avi_file)

    # parse the start time of the current avi file from its name
    time_start_avi = datetime.strptime(all_avi[i_avi], input_dir + '/%Y%m%d%H%M%S.%f.avi')

    # TODO verify that the computed span is close to this
    # time_next = datetime.strptime(all_avi[i_avi+1], input_dir + '/%Y%m%d%H%M%S.%f.avi')
    # # for 2 successive avi files with n_frames = 3
    # # file     : 1     2   ...
    # # frames   : 1 2 3 1 2 ...
    # # intervals:  1 2 3    ...
    # frame_step = (time_next - time_start_avi).total_seconds() / n_frames
    # line_step = frame_step / img_height
    # log.info('  time step for one frame is ' + \
    #            str(round(frame_step, ndigits=5)) + ' s')

    # loop over frames of that file
    i_f = 0
    while True:

        # read a frame
        s = t.b()
        img = iu.read_grey_frame(cap, log)
        if img is None :
            break
        log.debug('frame ' + str(i_f) + ' read' + t.e(s))

        # convert to 16-bit integers (for mean, division, etc.)
        s = t.b()
        img = img.astype(np.int16)
        log.debug('frame converted' + t.e(s))
        # iu.show('frame', img)

        # loop over scanned lines in that frame
        for i_l in range(0, img_height):

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

            # shift the index of the moving window
            i_w += 1
            # when the window is full, loop over the window
            if i_w == window_size :
                i_w = 0
                # log.debug('loop over moving window')

            # and of the output buffer
            i_o += 1
            
            # act on the image when it is complete
            if i_o == output_size :
                ss = t.b()
                i_o = 0

                # compute time of the first scan of this image
                time_end = time_start_avi + (i_f * img_height + i_l) * line_step
                time_start_frame = time_end - line_step * output_size
                # compute output name from time
                output_name = datetime.strftime(time_start_frame, '%Y-%m-%d_%H-%M-%S_%f')
                log.debug('output for ' + output_name)

                # Prepare (and store) flat-fielded image
                #----------------------------------------------------------

                # rotate to account for the orientation
                s = t.b()
                if top == 'right' :
                    output_img = np.flipud(output.T)
                elif top == 'left' :
                    output_img = np.fliplr(output.T)
                    # TODO check that this keeps the direction of motion from left to right in the final image
                log.debug('output image rotated' + t.e(s))

                if write_ff_image :
                    s = t.b()
                    output_file_name = os.path.join(output_dir_full, output_name + '_ff.png')
                    # TODO add end time or sampling freq?

                    cv2.imwrite(output_file_name, output_img * 255.)
                    # NB: apparently, the explicit conversion to uint8 is not necessary for imwrite
                    log.debug('output image written to disk' + t.e(s))


                # Process image
                #----------------------------------------------------------

                # describe distribution of grey levels though percentiles to:
                # - stretch the histogram and lighten the image a bit
                # - adapt the threshold to detect particles dynamically
                s = t.b()
                
                # rescale image to a smaller size to compute percentiles faster
                output_img_small = rescale(output_img, 0.2)
                # NB: a scale factor of 0.2 seems to be a good compromise between enhanced speed and representativity of the original image
                
                # compute the percentiles
                #                                        darkest, particle limit,         lighten limit, lightest
                grey_limits = np.percentile(output_img_small, (0, dark_threshold, 100 - light_threshold, 100))
                log.debug('output image grey levels measured' + t.e(s))
                
                if dark_threshold_method == 'dynamic' :
                    # use the percentiles
                    particles_threshold = grey_limits[1]
                    # add min bound to avoid being thrown off by large black stuff
                    # NB: typical thresholds on non noisy frames for ~1.5% percentile are ~ 0.85
                    #     on noisy frames they come down to ~0.7
                    #     so 0.6 is really is fallback, a safe bet
                    particles_threshold = max(particles_threshold, 0.6)
                    log.debug('dynamic dark threshold level : ' + str(particles_threshold))
                elif threshold_method == 'static' :
                    # disregard the percentile and use the number directly, rescaled to [0,1]
                    particles_threshold = dark_threshold / 100
                    # TODO check particles_threshold is in [0,1]
                else :
                    log.error('Unknown threshold method : ' + dark_threshold_method)
                
                # lighten the output image
                if grey_limits[2] < 1. :
                    s = t.b()
                    output_img = exposure.rescale_intensity(output_img, in_range=(0, grey_limits[2]))
                    log.debug('output image equalised and contrasted' + t.e(s))
                
                # write the processed image
                if write_processed_image :
                    s = t.b()
                    output_file_name = os.path.join(output_dir_full, output_name + '_processed.png')
                    # TODO add end time or sampling freq?
                    
                    cv2.imwrite(output_file_name, output_img * 255.)
                    # NB: apparently, the explicit conversion to uint8 is not necessary for imwrite
                    log.debug('output image written to disk' + t.e(s))
                
                # Extract particles
                #----------------------------------------------------------
                particles = ()
                if detect_particles :
                    # create output directory for particles
                    output_dir_particles = os.path.join(output_dir, output_name)
                    osu.checkmakedirs(output_dir_particles)
                    log.debug('output directory for particles created')
                    
                    # measure particles
                    s = t.b()
                    particles, properties, particles_mask = segment.segment(img=output_img, log=log, threshold=particles_threshold, dilate=dilate, min_area=min_area)
                    log.debug(str(len(particles)) + ' particles segmented' + t.e(s))
                    
                    # write column headers on the first line of the csv file
                    if first_row:
                        # compute column names with repetition for multi-element properties
                        properties_names = segment.extract_properties_names(properties[0], properties_labels)
                        # prepend other columns of interest
                        properties_names = ['dir','md5','date_time'] + properties_names
                        # write the header
                        csv_writer.writerow(properties_names)
                        log.debug('initialised csv file with header')
                        # turn the switch off!
                        first_row = False
                    
                    # process each particle
                    s = t.b()
                    complete_props = []
                    for i in range(len(particles)):

                        # write image
                        c_md5 = segment.write_particle_image(particles[i], output_dir_particles, log)

                        # extract properties of current particle
                        c_props = properties[i]
                    
                        # compute date time of capture of this particle
                        c_date_time = time_start_frame + int(round(c_props.centroid[1])) * line_step
                    
                        # extract and flatten properties of interest
                        c_props = segment.extract_properties(c_props, properties_labels)

                        # create a new line in the array of properties of interest
                        # NB: should match the headers written above
                        c_line = [output_name, c_md5, c_date_time] + c_props
                        # store it in the total list
                        complete_props = complete_props + [c_line]

                    log.debug('particles properties extracted and images saved' + t.e(s))

                    # write properties in the csv file
                    s = t.b()
                    csv_writer.writerows(complete_props)
                    # TODO check if we can reduce the number of decimal to reduce file size
                    log.debug('particles properties written to csv file' + t.e(s))
                    
                    # Write particles mask image
                    #------------------------------------------------------
                    if write_mask_image :

                        output_file_name = os.path.join(output_dir_full, output_name + '_mask.png')

                        # resize the source images to make the masked image a bit smaller
                        s = t.b()
                        output_img_small = rescale(output_img, scale=0.5) * 255.
                        particles_mask_small = rescale(particles_mask * 1.0, scale=0.5)
                        log.debug('output masked image rescaled' + t.e(s))

                        # create the masked image
                        s = t.b()
                        output_masked = iu.mask_image(output_img_small, particles_mask_small)
                        log.debug('output masked image created' + t.e(s))

                        # write the file
                        s = t.b()
                        cv2.imwrite(output_file_name, output_masked)
                        log.debug('output masked image written to disk' + t.e(s))

                    # end if write_mask_image

                # end if detect_particles
            
                log.info('%3d' % (len(particles)) + ' objects in ' + output_name + t.e(ss))
            # end process output image

        # end loop on frame lines
        
        # increment frame counter
        i_f += 1

    # end loop over avi file frames
    cap.release()

# end loop over avi files

if detect_particles :
    csv_handle.close()
    log.debug('particles csv file closed')
    # TODO close and reopen the file for each frame to be safer?

log.info('---END---')
