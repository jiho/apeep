import logging

import numpy as np
import pandas as pd
from itertools import product

import skimage.transform
import skimage.morphology

import torch
from detectron2.config import get_cfg
from detectron2.modeling import build_model
from detectron2.checkpoint import DetectionCheckpointer
import detectron2.data.transforms as T

import apeep.timers as t

from .segment import *

#from ipdb import set_trace as db

@t.timer
def semantic_segment(img, gray_threshold, predictor, sem_upsample_size, sem_n_batches=1, dilate=3, erode=2, sem_min_area=50, sem_max_area=300):
    """
    Segment an image into particles using semantic segmentation
    
    Args:
        img (ndarray): image (of type float) to segment
        gray_threshold (float): gray level threshold bellow which to consider particles
        predictor (detectron2.modeling.meta_arch.rcnn.GeneralizedRCNN): Detectron2 model to use for prediction
        sem_upsample_size (int): size of upsampled frames
        sem_n_batches (int): number of batches to distribute frames in
        dilate (int): after thresholding, particles are "grown" by 'dilate' 
            pixels to include surrounding pixels which may be part of the object 
            but are not dark enough. NB: if Otsu's tresholding is used, `dilate` 
            is increased to `4/3*dilate`.
        erode (int): after thresholding, particles are "shredded" by 'erode' 
            pixels to avoid including too many pixels. The combination of 
            dilation + erosion fills gaps in particles. 
        sem_min_area (int): minimum size of particles generated by semantic segmentation
        sem_max_area (int): maximum size of particles generated by semantic segmentation
        
    Returns:
        mask_lab (ndarray): labelled image (mask with each particle larger than `sem_min_area` and smaller 
            than `sem_max_area` numbered as an integer)
    """
    # get general logger
    log = logging.getLogger()
    
    # generate frames
    frames, frames_props = generate_frames(img, sem_upsample_size=sem_upsample_size)
    
    # predict frames
    predictions = predict_frames(
        frames=frames, 
        frames_props=frames_props, 
        n_batches=sem_n_batches,
        predictor=predictor
    )
    
    # generate new image with ROIs only
    img_rois = extract_rois(
        img=img,
        preds=predictions,
        dilate=dilate
    )
    
    # threshold image
    mask_lab = segment(
        img=img_rois, 
        gray_threshold=gray_threshold,
        dilate=dilate,
        erode=erode,
        min_area=sem_min_area,
        max_area=sem_max_area
    )
    
    return(mask_lab)


def create_predictor(model_weights, config_file, threshold):
    """
    Create a Detectron2 predictor
    
    Args:
        model_weights (str): path to model weights
        config_file (str): path to file with training model config
        threshold (float): threshold above which to consider detected objects in range ]0, 1[
        
    Returns:
        model (detectron2.modeling.meta_arch.rcnn.GeneralizedRCNN): Detectron2 model to use for prediction
    """
    
    # Get default config
    cfg = get_cfg()
    
    # Load training config
    cfg.merge_from_file(config_file)
    
    # Set detection threshold
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = threshold
    
    # Build model 
    model = build_model(cfg)
    # Load weights from training
    DetectionCheckpointer(model).load(model_weights)
    # Change mode to eval
    model.eval()
    
    return(model)



def generate_frames(img, nb_h_frames=5, nb_w_frames=26, frame_size=524, sem_upsample_size=800):
    """
    Generate frames from an Apeep image.
    
    Args:
        img (array): Apeep image
        nb_h_frames (int): number of frames to fit vertically in image
        nb_w_frames (int): number of frames to fit horizontally in image
        frame_size (int): frames size
        sem_upsample_size (int): size of upsampled frames
        
    Returns:
        frames (list(dict)): list of dicts with frames to predict formatted for Detectron2 prediction
        frames_props (dict): dict of frames label and coordinates
    """
    ## Convert large image to range [0, 255] and make it a 3 channels image
    if img.max() <= 1:
        img = img*255    
    img = np.stack([img, img, img], axis=2)
    
    # Initiate empty dict for frames properties
    frames_props = {
        'frame_label': [], # frame label
        'frame_row': [],   # #row of frame alignment (0 = first row of frames)
        'frame_col': [],   # #column of frame alignment (0 = first column of frames)
        'row0': [],        # frame top row
        'row1': [],        # frame bottom row
        'col0': [],        # frame left column
        'col1': [],        # frame right column
    }
    
    # Initiate empty list for frames
    frames = []
    
    # Create all combination of frames rows and cols
    frames_comb = list(product(range(0, nb_h_frames), range(0, nb_w_frames)))
    
    # Compute distance between two frame centers in height and width
    height, width, _ = img.shape
    h_dist = (height - frame_size) / (nb_h_frames - 1) # Distance between succesive frame centers in height
    w_dist = (width - frame_size)  / (nb_w_frames - 1) # Distance between succesive frame centers in width
    
    # Loop over frames
    for pos in frames_comb:
        
        ## Frame props
        # Extract frame row and col and create label
        frame_row = pos[0]
        frame_col = pos[1]
        label = frame_row + frame_row * (nb_w_frames - 1) + frame_col
        
        # Compute frame center in height and width
        h_center = round((frame_size / 2) + (frame_row * h_dist))
        w_center = round((frame_size / 2) + (frame_col * w_dist))
        
        # Compute frame limits
        row0 = int(h_center - frame_size/2)
        row1 = int(h_center + frame_size/2)
        col0 = int(w_center - frame_size/2)
        col1 = int(w_center + frame_size/2)
    
        # Append to dict
        frames_props['frame_label'].append(label)
        frames_props['frame_row'].append(frame_row)
        frames_props['frame_col'].append(frame_col)
        
        frames_props['row0'].append(row0)
        frames_props['row1'].append(row1)
        frames_props['col0'].append(col0)
        frames_props['col1'].append(col1)
        
        ## Frame
        # Extract frame
        frame = img[row0:row1, col0:col1, :].astype('uint8')
        # Create data augmentor to upsample frames
        aug1 = T.ResizeShortestEdge(short_edge_length=[sem_upsample_size], sample_style='choice')
        # Apply resizing
        frame = aug1.get_transform(frame).apply_image(frame)
        # Reshape frame from (H, W, C) to (C, H, W) for Detectron2 input and convert to tensor
        frame = torch.as_tensor(frame.astype('uint8').transpose(2, 0, 1))
        # Store in list of dicts with 'image', 'height' and 'width'
        frames.append({'image': frame, 'height': frame_size, 'width': frame_size})
    
    return(frames, frames_props)
    

def predict_frames(frames, frames_props, n_batches, predictor):
    """
    Generate Detectron2 predictions for a batch of frames.
    
    Args:
        frames (list(dict)): frames to predict as a list of dicts with frame as a tensor (C, H, W) in 'image' entry
        frames_props (dict): dict of frames label and coordinates
        n_batches (int): number of batches to distribute frames in
        predictor (detectron2.modeling.meta_arch.rcnn.GeneralizedRCNN): Detectron2 model to use for prediction
    
    Returns:
        preds (dataframe): predictions found in all frames of apeep image
    """

    ## Distribute frames into batches
    if n_batches > 1: # Case of 1 batch
        batches = [list(t) for t in np.array_split(frames, n_batches)]
    else: # Case of multiple batches
        batches = [frames]
    
    ## Predict batches frames at once
    # Initiate empty list to store predictions
    raw_preds = []
    with torch.no_grad():
        for batch in batches:
            raw_preds.extend(predictor(batch))
    
    ## Process predictions
    # Initiate empty dict to store image predictions
    preds = {
        'frame_label': [],
        'frame_row': [],
        'frame_col': [],
        'score': [],      # prediction score
        'bbox': [],       # predicted bbox
        'bbox_corr': [],  # predicted bbox corrected for frame position in image
        'mask': [],       # predicted mask
    }
    
    # Loop over predicted frames
    for i in range(len(frames)):
        ## Frames props
        # Extract frame labels
        frame_label = frames_props['frame_label'][i]
        frame_row = frames_props['frame_row'][i]
        frame_col = frames_props['frame_col'][i]
        
        # And coordinates
        row0 = int(frames_props['row0'][i]) # top row
        row1 = int(frames_props['row1'][i]) # bottom row
        col0 = int(frames_props['col0'][i]) # left column
        col1 = int(frames_props['col1'][i]) # right column
        
        ## Predictions
        instances = raw_preds[i]['instances'] # extract predictions
        # if instances found in frame, process them
        if len(instances) > 0:
            # Loop over prediction instances
            for idx in range(len(instances)):
                
                # Extract instance
                inst = instances[idx]
                
                # Extract prediction score
                score = inst.scores.cpu().numpy()[0]
                # Extract bbox
                bbox = inst.pred_boxes.tensor.cpu().numpy()[0]
                # Round and convert bbox values to int
                bbox = np.around(bbox).astype('int')
                # Correct bbox using frame TL coordinates (i.e. generate bbox in apeep image)
                bbox_corr = bbox + np.array((col0, row0, col0, row0))
                
                # Extract mask
                mask = inst.pred_masks.cpu().numpy()[0]
                
                # Store frame properties
                preds['frame_label'].append(frame_label)
                preds['frame_row'].append(frame_row)
                preds['frame_col'].append(frame_col)
                
                # Store predictions
                preds['score'].append(score)
                preds['bbox'].append(bbox)
                preds['bbox_corr'].append(bbox_corr)
                preds['mask'].append(mask)
    
    # Convert to dataframe
    preds = pd.DataFrame(preds)
    
    # Create a column for prediction index
    preds['pred_index'] = preds.index
    
    return(preds)


def extract_rois(img, preds, dilate=2):
    """
    Extract image backgound of bbox predictions by semantic segmentation model. 
    Return a blank image with only background of ROIs.

    Args:
        img (array): image 
        preds(df): predictions from Detectron2
        dilate (int): number of pixels to grow particles and bboxes with (dilation). 

    Returns:
        ndarray: white image with background for predicted bbox only 
    """
    # Get image dimensions
    h, w = img.shape
    
    # Create a blank mask for particles bbox and paste bbox
    img_blank = np.zeros_like(img)

    for i in preds.index:
        # Extract bbox of each prediction
        bbox = preds.loc[i, 'bbox_corr']
        # Replace prediction slice by 1
        img_blank[bbox[1]:bbox[3], bbox[0]:bbox[2]] = 1
        
    # Label bbox
    img_lab = skimage.measure.label(img_blank, background=False, connectivity=2)

    # Measure particles
    bbox_meas = skimage.measure.regionprops(label_image=img_lab)
    
    # Initiate new image with white background
    img_rois = np.ones_like(img)
    
    # Loop over bbox and paste image bbox content
    for i in range(len(bbox_meas)):
        
        # Get bbox of prediction
        bbox = bbox_meas[i].bbox
        
        # Extract bbox content slice with `dilate` extra px on each side so particle can be dilated
        # Make sure that slice do not cross images borders
        slice_bbox = (
            slice(max(0, bbox[0]-dilate), min(h, bbox[2]+dilate)), 
            slice(max(0, bbox[1]-dilate), min(w, bbox[3]+dilate))
        )
        
        # Paste bbox content into new image
        img_rois[slice_bbox] = img[slice_bbox]
    
    return(img_rois)


def check_bbox_overlap(bb1, bb2):
    """
    Check if two bbox overlap or not.

    Args:
        bb1 (list): coordinates of 1st bbox as [x1, y1, x2, y2] 
            The (x1, y1) position is at the top left corner,
            the (x2, y2) position is at the bottom right corner
        bb2 (list): coordinates of 2nd bbox as [x1, y1, x2, y2] 
            The (x1, y1) position is at the top left corner,
            the (x2, y2) position is at the bottom right corner

    Returns:
        bool: TRUE if there is an intersection, FALSE if not
    """
    # Determine the coordinates of the intersection rectangle
    x_left   = max(bb1[0], bb2[0])
    y_top    = max(bb1[1], bb2[1])
    x_right  = min(bb1[2], bb2[2])
    y_bottom = min(bb1[3], bb2[3])

    if x_right < x_left or y_bottom < y_top:
        inter = False
    else:
        inter = True
    
    return(inter)


def compute_bbox_union(bb1, bb2):
    """
    Compute the union of two bbox

    Args:
        bb1 (list): coordinates of 1st bbox as [x1, y1, x2, y2] 
            The (x1, y1) position is at the top left corner,
            the (x2, y2) position is at the bottom right corner
        bb2 (list): coordinates of 2nd bbox as [x1, y1, x2, y2] 
            The (x1, y1) position is at the top left corner,
            the (x2, y2) position is at the bottom right corner

    Returns:
        list: coordinates of bbox union as [x1, y1, x2, y2]
    """
    # Determine the coordinates of the union
    x_left   = min(bb1[0], bb2[0])
    y_top    = min(bb1[1], bb2[1])
    x_right  = max(bb1[2], bb2[2])
    y_bottom = max(bb1[3], bb2[3])

    bbox_union = [x_left, y_top, x_right, y_bottom]
    
    return(bbox_union)


def merge_masks(semantic_mask, regular_mask):
    """
    Merge semantic and regular image masks and return a labelled mask. 

    Args:
        semantic_mask (array): image mask generated by semantic segmentation
        regular_mask (array): image mask generated by gray level segmentation

    Returns:
        ndarray: merged image mask (particles as 1 and background as 0)
    """
    ## Compute mask overlap
    mask = np.logical_or(semantic_mask > 0, regular_mask > 0).astype(int)

    return(mask)