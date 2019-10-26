#
# Apeep, process ISIIS data without a peep
#
#
# (c) 2019 Jean-Olivier Irisson, GNU General Public License v3
#

# TODO use google style for docstrings https://github.com/google/styleguide/blob/gh-pages/pyguide.md#38-comments-and-docstrings
# TODO use descriptive style rather than imperative style in descriptions

import argparse
import glob
import logging
import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

import apeep
import apeep.timers as t
import apeep.im_pillow as im
# import apeep.im_opencv as im
# import apeep.im_lycon as im
# TODO rename this into im to avoid the confusion with the objects called img
from apeep import img_masked

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
    new_project = False
    if not os.path.exists(project_dir):
        print("This is a new project. Creating it")
        new_project = True
        os.makedirs(project_dir, exist_ok=True)

 
    ## Setup logging ----
    log = apeep.log(project_dir, debug=args.debug)
    log.debug("we're debugging !")


    ## Read configuration file ----
    cfg = apeep.configure(project_dir)
    
    # in the case of a new project, stop here
    if new_project:
        editor = os.getenv("VISUAL", os.getenv("EDITOR", "your_editor"))
        print("""
Now edit the configuration file. For example with
  {editor} {project}/config.yaml
You should at least set `io: input_dir` to something meaningful.
Other options are documented there
  https://github.com/jiho/apeep/blob/master/apeep/config.yaml""".format(editor=editor, project=project_dir))
        sys.exit()
    
    # add project directory to config, for ease of access by other functions
    cfg['io']['project_dir'] = project_dir

    # if the path to the input dir is relative,
    # make it relative to the project dir
    if not os.path.isabs(cfg['io']['input_dir']):
        cfg['io']['input_dir'] = os.path.join(project_dir, cfg['io']['input_dir'])

    ## Read environmental data ----
    all_txt = glob.glob(cfg['io']['input_dir'] + "/ISIIS*.txt")
    e = pd.DataFrame()
    for txt in all_txt:
        e = pd.concat([e,apeep.read_environ(txt)], ignore_index=True)
    nrows = len(e.index)
    if nrows == 0:
        log.warning("no environmental data found")
    else:
        log.info(str(len(e.index)) + " rows of environmental data")

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
    timer_img = t.b()
        
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
            elapsed = t.el(timer_ff, "flat-field")

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
                # rescale in [0,1] to save the image
                minv = output.min()
                maxv = output.max()
                output_0_1 = (output - minv) / (maxv - minv)
                # TODO check it more thouroughly but this normalisation creates very inhomogeneous grey levels in the result
                im.save(output_0_1, os.path.join(flat_fielded_image_dir, output_name + ".png"))

            # enhance output image
            if cfg['enhance']['go']:
                output = apeep.enhance(output, cfg)
                
                if cfg['enhance']['write_image']:
                    enhanced_image_dir = os.path.join(project_dir, "enhanced")
                    os.makedirs(enhanced_image_dir, exist_ok=True)
                    im.save(output, os.path.join(enhanced_image_dir, output_name + ".png"))
            
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
                    im.save(output_labelled == 0, os.path.join(segmented_image_dir, output_name + ".png"))
                
                if cfg['segment']['write_masked_image']:
                    masked_image_dir = os.path.join(project_dir, "masked")
                    os.makedirs(masked_image_dir, exist_ok=True)
                    img_masked.save_masked(img=output, labels=output_labelled, \
                        dest=os.path.join(masked_image_dir, output_name), format=['rgb', 'psd'])
            
            # measure
            if cfg['measure']['go']:
                particles, particles_props = apeep.measure(
                    img=output,
                    img_labelled=output_labelled,
                    props=cfg['measure']['properties']
                )
                if cfg['measure']['write_particles']:
                    particles_images_dir = os.path.join(project_dir, "particles", output_name)
                    os.makedirs(particles_images_dir, exist_ok=True)
                    # write particles images
                    apeep.write_particles(particles, particles_images_dir)      
                    # and properties
                    apeep.write_particles_props(particles_props, particles_images_dir)
            
            # compute performance
            elapsed = t.e(timer_img)
            real_time = cfg['enhance']['image_size'] / cfg['acq']['scan_per_s']
            log.info(f"{output_name} done ({elapsed:.3f}s @ {real_time/elapsed:.2f}x)")
            
            # reset flat-fielding and global timers for next iteration
            timer_ff = t.b()
            timer_img = t.b()
            

if __name__ == "__main__":
    main()
