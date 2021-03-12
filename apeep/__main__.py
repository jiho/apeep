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
import tarfile
import shutil

import numpy as np
import pandas as pd

import apeep
import apeep.timers as t
#import apeep.im_pillow as im
import apeep.im_opencv as im
#import apeep.im_lycon as im
from apeep import stack
#from ipdb import set_trace as db


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
    # also correct path for semantic model weights     
    if not os.path.isabs(cfg['segment']['sem_model_path']):
        cfg['segment']['sem_model_path'] = os.path.join(project_dir, cfg['segment']['sem_model_path'])
        
    ## Initiate particles properties dataframe ----
    all_particles_props = pd.DataFrame()
        
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
    output_buffer = np.empty((output_size, img_width))
    i_o = 0
    
    ## Read environmental data ----
    # get name of first avi file
    first_input = next(input_stream)
    first_avi = os.path.split(first_input['filename'])[-1]
    
    log.debug("read environmental data")
    all_environ = glob.glob(cfg['io']['input_dir'] + "/ISIIS*.txt")
    e = [apeep.read_environ(f, first_avi) for f in all_environ]
    if len(e) > 0:
        e = pd.concat(e, ignore_index=True)
        log.info(str(len(e.index)) + " rows of environmental data")
    else:
        e = pd.DataFrame()
        log.warning("no environmental data found")
        
    # initialise sub-sampling
    # compute n as in subsampling_rate = 1/n
    subsampling_lag = round(1/cfg['subsampling']['subsampling_rate'])
    # initialise counter
    subsampling_count = -cfg['subsampling']['first_image'] 
    log.info("processing with a subsampling rate of " + str(cfg['subsampling']['subsampling_rate']) + " (1 image processed every " + str(subsampling_lag) + " images)")
    log.info("starting at image number  " + str(cfg['subsampling']['first_image']))
    
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
            # TODO we're doing np.sum with axis 0 (=per column) on a C contiguous array, although and F contiguous array would be faster. Look into changing this.
            
            # compute flat-fielding
            piece['data'] = piece['data'] / mavg
        
        # log.debug("add block to output buffer")
        output_buffer[i_o:i_o+step,:] = piece['data']
        
        # store transect name, avi file, frame number and line number at beginning of image
        if i_o == 0:
            image_info = {
                'transect_name': cfg['io']['input_dir'].split('/')[-1] if len(cfg['io']['input_dir'].split('/')[-1]) > 0 else cfg['io']['input_dir'].split('/')[-2],
                'start_avi_file': os.path.split(piece['filename'])[1],
                'start_frame_nb': piece['frame_nb'],
                'start_line_nb': piece['line_nb']
            }        
        i_o = i_o + step
        
        # when output_buffer is full
        if i_o == output_size:
            # end timer for flat-fielding
            elapsed = t.el(timer_ff, "flat-field")

            # reinitialise output_buffer
            i_o = 0
            
             # store avi file, frame number and line number at end of image
            image_info.update({
                'end_avi_file': os.path.split(piece['filename'])[1],
                'end_frame_nb': piece['frame_nb'],
                'end_line_nb': piece['line_nb']
            })    
            
            # rotate the image so that motion is from the left to the right
            timer_rot = t.b()
            if cfg['acq']['top'] == "right":
                output = np.rot90(output_buffer).copy(order="C")
            elif cfg['acq']['top'] == "left":
                output = np.transpose(output_buffer).copy(order="C")
            # NB: the copy with C order takes time but the operations are faster afterwards and it is worth it
            elapsed = t.el(timer_rot, "rotate")
            # TODO rotate the final particles only and check wether this is faster

            # compute the time stamp of the image
            # start of avi file + n frames + n lines in the last frame
            time_end =  piece['start'] + \
                        piece['frame_nb'] * frame_timestep + \
                        piece['line_nb'] * line_timestep
            time_start = time_end - (output_size * line_timestep)
            output_name = datetime.strftime(time_start, '%Y-%m-%d_%H-%M-%S_%f')
            
            image_info.update({
                'img_name': output_name
            })
            
            # increment subsample counter
            subsampling_count = subsampling_count + 1
            
            # process 1 image every 'subsample_rate'
            # if subsample counter is divisible by sumsampling_rate and first image to process is reached
            if (subsampling_count%subsampling_lag == 0 and subsampling_count >= 0):
            
                if cfg['flat_field']['go']:
                    # rescale in [0,1] to save the image
                    minv = output.min()
                    maxv = output.max()
                    output_0_1 = (output - minv) / (maxv - minv)
                    # TODO check it more thouroughly but this normalisation creates very inhomogeneous grey levels in the result
                
                    if cfg['flat_field']['write_image']:
                        flat_fielded_image_dir = os.path.join(project_dir, "flat_fielded")
                        os.makedirs(flat_fielded_image_dir, exist_ok=True)
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
                    # compute gray segmentation threshold
                    gray_threshold = apeep.segmentation_threshold(
                        output,
                        method=cfg['segment']['method'],
                        threshold=cfg['segment']['threshold'],
                        var_limit=cfg['segment']['var_limit']
                    )
                    
                    if cfg['segment']['pipeline'] == 'semantic':
                        # run semantic segmentation
                        output_labelled = apeep.semantic_segment(
                            output, 
                            gray_threshold=gray_threshold, 
                            sem_model_path=cfg['segment']['sem_model_path'], 
                            sem_conf_threshold=cfg['segment']['sem_conf_threshold'], 
                            dilate=cfg['segment']['dilate'], 
                            erode=cfg['segment']['erode'], 
                            sem_min_area=cfg['segment']['sem_min_area'], 
                            sem_max_area=cfg['segment']['sem_max_area']
                        )
                       
                    elif cfg['segment']['pipeline'] == 'regular':
                        # run regular segmentaion
                        output_labelled = apeep.segment(
                            output,
                            gray_threshold=gray_threshold,
                            dilate=cfg['segment']['dilate'],
                            erode=cfg['segment']['erode'],
                            min_area=cfg['segment']['reg_min_area']
                        )
                        
                    elif cfg['segment']['pipeline'] == 'both':
                        # run semantic segmentation
                        output_sem = apeep.semantic_segment(
                            output, 
                            gray_threshold=gray_threshold, 
                            sem_model_path=cfg['segment']['sem_model_path'], 
                            sem_conf_threshold=cfg['segment']['sem_conf_threshold'], 
                            dilate=cfg['segment']['dilate'], 
                            erode=cfg['segment']['erode'], 
                            sem_min_area=cfg['segment']['sem_min_area'], 
                            sem_max_area=cfg['segment']['sem_max_area']
                        )
                        
                        # run regular segmentaion
                        output_reg = apeep.segment(
                            output,
                            gray_threshold=gray_threshold,
                            dilate=cfg['segment']['dilate'],
                            erode=cfg['segment']['erode'],
                            min_area=cfg['segment']['reg_min_area']
                        )
                        
                        # merge masks
                        output_labelled = apeep.merge_masks(
                            semantic_mask=output_sem,
                            regular_mask=output_reg,
                        )
                    
                    
                    if cfg['segment']['write_image']:
                        segmented_image_dir = os.path.join(project_dir, "segmented")
                        os.makedirs(segmented_image_dir, exist_ok=True)
                        im.save(output_labelled == 0, os.path.join(segmented_image_dir, output_name + ".png"))
                    
                    if cfg['segment']['write_stack']:
                        stack_image_dir = os.path.join(project_dir, "stacked")
                        os.makedirs(stack_image_dir, exist_ok=True)
                        stack.save_stack(img=output, labels=output_labelled, \
                            dest=os.path.join(stack_image_dir, output_name), format=cfg['segment']['stack_format'])
                
                # measure
                if cfg['measure']['go'] and np.sum(output_labelled) != 0 :
                    particles, particles_props = apeep.measure(
                        img=output,
                        img_labelled=output_labelled,
                        image_info=image_info,
                        props=cfg['measure']['properties']
                    )
                    
                    if cfg['measure']['write_particles']:
                        particles_images_dir = os.path.join(project_dir, "particles", output_name)
                        os.makedirs(particles_images_dir, exist_ok=True)
                        
                        # merge particles and environment data
                        particles_props = apeep.merge_environ(e, particles_props, output_name)
                        
                        # write particles images
                        apeep.write_particles(particles, particles_images_dir, px2mm=cfg['acq']['window_height_mm']/img_width)      
                        # and properties
                        apeep.write_particles_props(particles_props, particles_images_dir)
                        
                        
                        if cfg['measure']['as_tar']:
                            # Create a tar archive containing particles and properties 
                            with tarfile.open(particles_images_dir + '.tar', 'w') as tar:
                                tar.add(particles_images_dir, arcname=os.path.basename(particles_images_dir))
                                tar.close()
                            
                            # Delete directory 
                            shutil.rmtree(particles_images_dir)
                        
                                    
            # compute performance
            elapsed = t.e(timer_img)
            real_time = cfg['enhance']['image_size'] / cfg['acq']['scan_per_s']
            log.info(f"{output_name} done ({elapsed:.3f}s @ {real_time/elapsed:.2f}x)")
            
            # reset flat-fielding and global timers for next iteration
            timer_ff = t.b()
            timer_img = t.b()
                
if __name__ == "__main__":
    main()
