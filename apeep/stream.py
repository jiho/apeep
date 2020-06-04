import glob
import logging
import os
import datetime

import av
import numpy as np
import pandas as pd

# from ipdb import set_trace as db

def stream(dir, n=1):
    """
    Get a stream of lines of pixels from a directory
    
    ISIIS scans lines, hence creating a continuous stream of lines of pixels. 
    This stream is cut into 2048x2048 frames (lines are scanned from top to
    bottom in each frame), which are stored in successive avi files.
    This generator abstracts that storage, loops over avi files and their
    frames to return blocks of `n` scanned lines at a time
    
    Args:
        dir (str): path to input directory containing .avi files
        n (int): number of lines of the stream to return at each iteration
    
    Yields:
         dict: containing
            filename (str): name of the current avi file.
            timecode (datetime): timecode for the start of the current avi file (deduced from its name).
            frame_nb (int): number of the frame in the current avi file, starting from 0.
            line_nb (int): number of the last lined included into this block of data.
            data (ndarray): `n` lines of data as a numpy array of floats in [0,1].
    """
    # get general logger
    log = logging.getLogger()

    # check existence of input directory
    if not os.path.isdir(dir):
        raise FileNotFoundError("input directory " + dir + " does not exist")

    # list available avi files
    all_avi = glob.glob(dir + "/*.avi")
    # TODO check whether glob gets executed once or at every iteration of stream()
    # sort them in alphanumeric order (glob.glob() does not)
    all_avi.sort()
    n_avi = len(all_avi)
    if n_avi == 0:
        raise RunTimeError("no avi files in " + dir)
    log.debug("found " + str(n_avi) + " avi files in '" + dir + "'")

    # TODO check that n is a divisor of 2048 = 1, 2, 4, 8, etc.

    # initialise the block of data to be returned
    block = np.empty((n, 2048))
    i_b = 0

    # iterate over files
    for avi in all_avi:
        log.debug("open '" + avi + "'")

        timecode = datetime.datetime.strptime(os.path.basename(avi), "%Y%m%d%H%M%S.%f.avi")
        # TODO check for jumps in the video file time stamps

        v = av.open(avi)
        # TODO reconsider cv2 here because av actually has a lot of dependencies!
        
        # iterate over video frames of this file
        i_f = 0
        for frame in v.decode(video=0):
            log.debug("get frame " + str(i_f))
            
            # convert this frame into a "greyscale" numpy array
            arr = np.asarray(frame.to_image())[:,:,0]
            # NB: frame.to_ndarray does not work with ISIIS frames which are 
            #     in the lab8 color space.

            # fill the block of data we want, line by line
            for i_l in range(arr.shape[0]):
                block[i_b,:] = arr[i_l,:]
                i_b += 1
                # when the block is full, return it and reinitialise it
                if i_b == n:
                    # TODO check if there is a better/faster way to do this; this performs the if test for every line
                    yield({
                        'filename': avi,
                        'start': timecode,
                        'frame_nb': i_f,
                        'line_nb': i_l,
                        'data': block/255.
                    })
                    # reinitialise block index
                    i_b = 0
            
            # increase frame index
            i_f += 1

