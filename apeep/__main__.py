#
# Apeep, process ISIIS data without a peep
#
#
# (c) 2019 Jean-Olivier Irisson, GNU General Public License v3
#

import argparse
import glob
import logging
import os
import sys
from datetime import datetime, timedelta

import numpy as np

import apeep
import apeep.timers as t
import apeep.img_pillow as img
# import apeep.img_lycon as img

# from ipdb import set_trace as db

def main():
    
    ## Parse command line arguments ----
    parser = argparse.ArgumentParser(
        prog="apeep",
        description="Process ISIIS data without a peep"
    )
  
    parser.add_argument("path", type=str, nargs=1,
        help="path to the project.")
    parser.add_argument("-d", "--debug", dest="debug", action="store_true",
        help="print debug messages.")

    args = parser.parse_args()
 
    # make sure project directory exists
    project_dir = args.path[0]
    os.makedirs(project_dir, exist_ok=True)
    # TODO check whether it exists already and stop early if it does not, instructing to edit config.yaml

 
    ## Setup logging ----
    log = apeep.log(project_dir, debug=args.debug)
    log.debug("we're debugging !")


    ## Read configuration file ----
    cfg = apeep.configure(project_dir)
    # add project directory, for ease of access by other functions
    cfg['io']['project_dir'] = project_dir


    ## Setup processing loop ----
    # hardcode frame dimensions
    img_height = 2048
    img_width  = 2048
    # TODO allow this to not be hardcoded
    
    log.debug("compute time intervals")
    # compute time step for each frame or each scanned line
    line_timestep = 1. / cfg['acq']['scan_per_s']
    # TODO infer scan_per_s from the first few avi files
    frame_timestep = line_timestep * img_height
    # convert to time spans
    line_timestep = timedelta(seconds=line_timestep)
    frame_timestep = timedelta(seconds=frame_timestep)
    
    log.debug("initialise moving average line")
    step = cfg['flat_field']['step_size']
    # make window_size a multiple of step_size
    window_size = int(cfg['flat_field']['window_size'] / step) * step
    # get data in the first window and compute the mean
    input_stream = apeep.stream(dir=cfg['io']['input_dir'], n=window_size)
    window = next(input_stream)
    mavg = np.mean(window['data'], axis=0) # columnw-wise mean
    log.debug("moving average line initialised, mean value = " + str(np.mean(mavg)))
    
    log.debug("initialise output image")
    # make output_size a multiple of step_size
    output_size = int(cfg['enhance']['image_size'] / step) * step
    output = np.empty((output_size, img_width))
    i_o = 0
    
    # initialise flat-fielding timer
    timer_ff = t.b()
        
    # loop over files
    input_stream = apeep.stream(dir=cfg['io']['input_dir'], n=step)
    for piece in input_stream:
        
        # flat-field
        if cfg['flat_field']['go']:
            # update the moving average using an exponential decay approximation
            # NB: allows to not store the actual window
            #     faster than recomputing the whole mean every time
            # NB: computing the median is another order of magnitude slower
            mavg = mavg + (np.sum(piece['data'], axis=0) - mavg * step) / window_size
            # log.debug("moving average line updated, mean value = " + str(np.mean(mavg)))
            
            # compute flat-fielding
            piece['data'] = piece['data'] / mavg
        
        # log.debug("add block to output image")
        output[i_o:i_o+step,:] = piece['data']
        i_o = i_o + step
        
        # when output is full
        if i_o == output_size:
            # end timer for flat-fielding
            t.e(timer_ff, "flat-field")

            # reinitialise output image
            i_o = 0
            
            # TODO rotate towards horizontal
        
            # compute the time stamp of the image
            # start of avi file + n frames + n lines in the last frame
            time_end =  piece['start'] + \
                        piece['frame_nb'] * frame_timestep + \
                        piece['line_nb'] * line_timestep
            time_start = time_end - (output_size * line_timestep)
            output_name = datetime.strftime(time_start, '%Y-%m-%d_%H-%M-%S_%f')

            if cfg['flat_field']['write_image']:
                flat_fielded_image_dir = os.path.join(project_dir, "flat_fielded")
                os.makedirs(flat_fielded_image_dir, exist_ok=True)
                minv = output.min()
                maxv = output.max()
                output_0_1 = (output - minv) / (maxv - minv)
                img.save(output_0_1, os.path.join(flat_fielded_image_dir, output_name + ".png"))

            # enhance output image
            if cfg['enhance']['go']:
                output = apeep.enhance(output, cfg)
                
                if cfg['enhance']['write_image']:
                    enhanced_image_dir = os.path.join(project_dir, "enhanced")
                    os.makedirs(enhanced_image_dir, exist_ok=True)
                    img.save(output, os.path.join(enhanced_image_dir, output_name + ".png"))
            
            # segment
            if cfg['segment']['go']:
                output_labelled = apeep.segment(output,
                    method=cfg['segment']['method'],
                    threshold=cfg['segment']['threshold'],
                    dilate=cfg['segment']['dilate'],
                    min_area=cfg['segment']['min_area']
                )
                if cfg['segment']['write_image']:
                    segmented_image_dir = os.path.join(project_dir, "segmented")
                    os.makedirs(segmented_image_dir, exist_ok=True)
                    img.save(output_labelled == 0, os.path.join(segmented_image_dir, output_name + ".png"))
                
                if cfg['segment']['write_masked_image']:
                    masked_image_dir = os.path.join(project_dir, "masked")
                    os.makedirs(masked_image_dir, exist_ok=True)

                    # colour image
                    masked = np.zeros((output_size, img_width, 3))
                    masked[:,:,0] = (output + 1/255) * (output_labelled == 0)  # B
                    masked[:,:,1] = (output + 1/255) * (output_labelled == 0)  # G
                    masked[:,:,2] = (output + 1/255) * (output_labelled != 0)  # R
                    img.save(masked, os.path.join(masked_image_dir, output_name + "_clr.png"))
                    
                    # multilayer, coloured TIFF file
                    from PIL import Image
                    # create background as RGB
                    back = np.zeros((output_size, img_width, 3), dtype="uint8")
                    back[:,:,0] = output * 255
                    back[:,:,1] = back[:,:,0]
                    back[:,:,2] = back[:,:,0]
                    back_img = Image.fromarray(back)
                    # create mask as RGBA
                    mask = np.zeros((output_size, img_width, 4), dtype="uint8")
                    mask[:,:,0] = (output_labelled != 0) * 255
                    mask[:,:,3] = mask[:,:,0]
                    mask_img = Image.fromarray(mask)                    
                    # save as multipage TIFF
                    back_img.save(os.path.join(masked_image_dir, output_name + ".tif"), format="tiff", append_images=[mask_img], save_all=True, compression='tiff_lzw')
            
            # measure
            # TODO implement
            
            # start flat-fielding timer for next iteration
            timer_ff = t.b()
            # TODO add total timer per output frame
            

if __name__ == "__main__":
    main()
