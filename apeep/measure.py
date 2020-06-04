import logging
import os

import skimage.measure
import numpy as np
import hashlib
import pandas as pd

import apeep.timers as t
# import apeep.im_pillow as im
import apeep.im_opencv as im
# TODO homogenise the image saving with the rest

#from ipdb import set_trace as db

@t.timer
def measure(img, img_labelled, props=['area']):
    """
    Measure particles
    
    Args:
        img (ndarray): image (of type float)
        img_labelled (ndarray): labelled image (mask with each particle 
            numbered as an integer)
        properties (list): list of properties to extract from each particle
    
    Returns:
        particles (dict): dict of ndarrays containing particles; the keys are
            their md5 checksum
        partitles_props (dataframe): dataframe containing their
            properties, suitable to be turned into a pandas DataFrame
    """

    # TODO add bounding box at minima

    # get general logger
    log = logging.getLogger()

    # initiate particle measurements
    regions = skimage.measure.regionprops(label_image=img_labelled, intensity_image=img)
    
    # extract the content of the particles
    particles = [get_particle_array(r) for r in regions]
    # uniquement identify particles with their md5 checksum
    particles = {hashlib.md5(p).hexdigest():p for p in particles}
    
    log.debug(f"{len(particles)} particles")

    # store this as their first property
    particle_props = {'id': list(particles.keys())}    
    # append the other properties we need
    # NB: append so that the md5 column is the first one
    particle_props.update(skimage.measure._regionprops._props_to_dict(regions, properties=props))
    # alternative to using this private method
    # particle_props.update(measure.regionprops_table(
    #     label_image=img_labelled,
    #     intensity_image=img,
    #     properties=props
    # ))
    
    # convert to dataframe
    particle_props = pd.DataFrame(particle_props)
    
    # add "object_" to column names 
    particle_props.columns = "object_" + particle_props.columns
    
    return (particles, particle_props)

def get_particle_array(x):
    """
    Extract the particle pixels and blank out the outside
    
    Args:
        x (RegionProperties): from skimage.measure.region_props
    
    Returns:
        (ndarray) of floats containing the particle values
    """
    # extract the particle region
    particle = x._intensity_image[x._slice] * 0.997
    # mask the outside of the particle with white
    particle = np.where(x._label_image[x._slice] == x.label, particle, 1.)
    return(particle)


@t.timer
def write_particles_props(particles_props, destination):
    """
    Write a set of particles to disk
    
    Args:
        particles_props (dataframe): dataframe of particles properties
            generated by apeep.measure
        destination (str): path to the directory where *particles* are
            (i.e. has the subdirectory below "particles")
    
    Returns:
        Nothing
    """

    # split the destination directory
    base_dir = os.path.dirname(destination)
    sub_dir = os.path.basename(destination)
        
    # write to file
    particles_file = os.path.join(base_dir, "ecotaxa_particles.tsv")
    # if file does't exist, create file with appropriate first row
    if not os.path.exists(particles_file):
        
        # add first row, containing data format codes; [f] for floats, [t] for text
        # initiate first_row as floats
        first_row = ['[f]'] * (particles_props.shape[1])
        
        # list of possible columns with data format as text [t]
        as_text = ['img_file_name',
                   'object_id',
                   'object_avi_file',
                   'object_frame',
                   'object_line_in_frame',
                   'object_time',
                   'object_date',
                   'sample_id',
                   'object_label']
        
        # for columns in particles_props and with text format, change first row to [t]
        col_ind_text = [particles_props.columns.get_loc(col) for col in list(set(particles_props.columns) & set(as_text))]
        for i in col_ind_text:
            first_row[i] = '[t]'

            
        # first_row as Dataframe row with appropriate headers
        first_row = pd.DataFrame(first_row).T
        first_row.columns = particles_props.columns
        
        # concat first_row and dataframe
        particles_props = pd.concat([first_row, particles_props], ignore_index = True)
        
        # initialise, with headers
        particles_props.to_csv(particles_file,
            index=False, sep="\t", header=True)
    else:
        # just append to the file
        with open(particles_file, "a") as outfile:
            particles_props.to_csv(outfile,
                index=False, sep="\t", header=False)
    pass


def get_particles_props(particles_props, destination):
    """
    Write a set of particles to disk
    
    Args:
        particles_props (dict): dictionnary of particles properties
            generated by apeep.measure
        destination (str): path to the directory where *particles* are
            (i.e. has the subdirectory below "particles")
    
    Returns:
        (DataFrame) with particles properties
    """
    # split the destination directory
    sub_dir = os.path.basename(destination)
    
    # convert to pandas DataFrame
    df_particles = pd.DataFrame(particles_props)
    # add "object_" to column names 
    df_particles.columns = "object_" + df_particles.columns
    
    # for EcoTaxa:
    # compute image file name
    df_particles['img_file_name'] = sub_dir + "/" + df_particles['object_id'] + ".png"
    
    # compute date_time
    df_particles["object_date_time"] = pd.to_datetime(sub_dir, format="%Y-%m-%d_%H-%M-%S_%f")
    
    # compute time
    df_particles["object_time"] = pd.to_datetime(df_particles.object_date_time, format="%Y-%m-%d_%H-%M-%S_%f").dt.strftime('%H%M%S')

    # compute date
    df_particles["object_date"] = pd.to_datetime(df_particles.object_date_time, format="%Y-%m-%d_%H-%M-%S_%f").dt.strftime('%Y%m%d')    
        
    return(df_particles)

@t.timer
def write_particles(particles, destination, px2mm):
    """
    Write a set of particles to disk
    
    Args:
        particles (dict): dictionnary of particles generated by apeep.measure
        destination (str): path to the destination directory
    
    Returns:
        Nothing
    """
    for name,part in particles.items():
        # add scale
        part = add_scale(part, px2mm)
        im._save(part, os.path.join(destination, name + ".png"))
    pass

# define a custom minimal "font"
f1 = np.asarray(\
[[1,1,0,1],\
 [1,0,0,1],\
 [1,1,0,1],\
 [1,1,0,1],\
 [1,1,0,1],\
 [1,1,0,1],\
 [1,1,0,1]])
f2 = np.asarray(\
[[1,1,0,0,1,1],\
 [1,0,1,1,0,1],\
 [1,1,1,0,1,1],\
 [1,1,0,1,1,1],\
 [1,0,1,1,1,1],\
 [1,0,1,1,1,1],\
 [1,0,0,0,0,1]])
f0 = np.asarray(\
[[1,0,0,1,1],\
 [0,1,1,0,1],\
 [0,1,1,0,1],\
 [0,1,1,0,1],\
 [0,1,1,0,1],\
 [0,1,1,0,1],\
 [1,0,0,1,1]])
fm = np.asarray(\
[[1,1,1,1,1,1],\
 [1,1,1,1,1,1],\
 [1,1,1,1,1,1],\
 [1,0,0,1,0,1],\
 [1,0,1,0,1,0],\
 [1,0,1,0,1,0],\
 [1,0,1,0,1,0]])
# define scale bar text
t1mm  = np.concatenate((f1,fm,fm),    axis=1)
t10mm = np.concatenate((f1,f0,fm,fm), axis=1)
t20mm = np.concatenate((f2,f0,fm,fm), axis=1)
# breaks_mm = np.array([1, 10, 20])
# breaks_text = [t1mm, t10mm, t20mm]
breaks_mm = np.array([1, 10])
breaks_text = [t1mm, t10mm]

def add_scale(img, px2mm):
    img_width_px = img.shape[1]
    
    # define how large the scale bar is for each physical size,
    # depending on the resolution
    breaks_px = np.round(breaks_mm / px2mm)
    
    # find the most appropriate scale bar size given the width of the object
    break_idx = int(np.interp(img_width_px, breaks_px, range(len(breaks_px))))
    
    # pick the elements we need
    bar_width_px = int(breaks_px[break_idx])
    break_text = breaks_text[break_idx]
    text_width_px = break_text.shape[1]
    
    # define the width and height of the scale bar
    w = max(img_width_px, bar_width_px, text_width_px)
    h = 29
    
    # pad the input image on the right if it is now wide enough
    if w > img_width_px:
        padding = w - img_width_px
        img = np.pad(img, ((0,0),(0,padding)), constant_values=1)
    
    # draw a blank scale
    scale = np.ones((h, w))
    # add the scale bar
    scale[slice(h-2,h), slice(0,bar_width_px)] = 0
    # add the text
    scale[slice(h-4-7,h-4), slice(0,text_width_px)] = break_text
    
    # combine with the image
    img = np.concatenate((img, scale), axis=0)
    
    # add a bit of padding to make it nice
    # (and make the scale bar 31px high in total, like for zooscan, uvp, etc.)
    img = np.pad(img, 2, constant_values=1)

    return(img)

