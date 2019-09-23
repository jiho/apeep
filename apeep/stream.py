import glob
import logging
import os

import av
import numpy as np

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
         ndarray: block of `n` lines as a numpy array of uint8 (i.e. in [0,255])
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
        v = av.open(avi)
        # TODO check for jumps in the video file time stamps
        
        # iterate over video frames of this file
        i_f = 0
        for frame in v.decode(video=0):
            log.debug("get frame " + str(i_f))
            i_f += 1
            
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
                    yield(block/255.)
                    i_b = 0
