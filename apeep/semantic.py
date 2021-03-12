import logging

import numpy as np
import pandas as pd
from itertools import product

import skimage.transform
import skimage.morphology

from detectron2 import model_zoo
from detectron2.config import get_cfg
from detectron2.engine import DefaultPredictor
import apeep.timers as t

from .segment import *

#from ipdb import set_trace as db

@t.timer
def semantic_segment(img, gray_threshold, predictor, dilate=3, erode=2, sem_min_area=50, sem_max_area=300):
    """
    Segment an image into particles using semantic segmentation
    
    Args:
        img (ndarray): image (of type float) to segment
        gray_threshold (float): gray level threshold bellow which to consider particles
        predictor (detectron2.engine.defaults.DefaultPredictor): Detectron2 model to use for prediction
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
        mask
    """
    # get general logger
    log = logging.getLogger()
    
    # generate frames
    frames = generate_frames(img)
    
    # predict frames
    predictions = predict_frames(
        img=img, 
        frames_props=frames, 
        predictor=predictor
    )
    
    # resolve overlaps
    predictions = resolve_overlaps(img_preds=predictions)
    
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


def create_predictor(model_path, threshold, nb_classes=1):
    """
    Create a Detectron2 predictor
    
    Args:
        model_path (str): path to model weights
        threshold (float): threshold above which to consider detected objects in range ]0, 1[
        nb_classes (int): number of classes to predict
        
    Returns:
        predictor (detectron2.engine.defaults.DefaultPredictor): Detectron2 model to use for prediction
    """
    # Get default config
    cfg = get_cfg()
    # Customize predictor
    cfg.merge_from_file(model_zoo.get_config_file('COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml'))
    cfg.MODEL.WEIGHTS = model_path
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = nb_classes
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = threshold
    predictor = DefaultPredictor(cfg)
    
    return(predictor)



def generate_frames(img, nb_h_frames=5, nb_w_frames=6, frame_size=524):
    """
    Generate frames coordinates in an Apeep image.
    
    Args:
        img (array): Apeep image
        nb_h_frames (int): number of frames to fit vertically in image
        nb_w_frames (int): number of frames to fit horizontally in image
        frame_size (int): frames size
        
    Returns:
        frames_props (dict): dict of frames label and coordinates
    """
    #TODO: does args  nb_h_frames, b_w_frames and frame_size have to be hardcoded?
    
    # Initiate empty dict for frames properties
    frames_props = {
        'frame_label': [], # frame label
        'frame_row': [],   # #row of frame alignment (0 = first row of frames)
        'frame_col': [],   # #column of frame alignment (0 = first column of frames)
        'h_center': [],    # vertical frame center 
        'w_center': [],    # horizontal frame center
        'row0': [],        # frame top row
        'row1': [],        # frame bottom row
        'col0': [],        # frame left column
        'col1': [],        # frame right column
    }
    
    # Create all combination of frames rows and cols
    all_frames = list(product(range(0, nb_h_frames), range(0, nb_w_frames)))
    
    # Compute distance between two frame centers in height and width
    height, width = img.shape
    h_dist = (height - frame_size) / (nb_h_frames - 1) # Distance between succesive frame centers in height
    w_dist = (width - frame_size)  / (nb_w_frames - 1) # Distance between succesive frame centers in width
    
    # Loop over frames
    for frame in all_frames:
        
        # Extract frame row and col and create label
        frame_row = frame[0]
        frame_col = frame[1]
        label = frame_row + frame_row * (nb_w_frames - 1) + frame_col
        
        # Compute frame center in height and width
        h_center = round((frame_size / 2) + (frame_row * h_dist))
        w_center = round((frame_size / 2) + (frame_col * w_dist))
        
        # Compute frame limits
        row0 = h_center - frame_size/2
        row1 = h_center + frame_size/2
        col0 = w_center - frame_size/2
        col1 = w_center + frame_size/2
    
        # Append to dict
        frames_props['frame_label'].append(label)
        frames_props['frame_row'].append(frame_row)
        frames_props['frame_col'].append(frame_col)
        
        frames_props['h_center'].append(h_center)
        frames_props['w_center'].append(w_center)
        
        frames_props['row0'].append(row0)
        frames_props['row1'].append(row1)
        frames_props['col0'].append(col0)
        frames_props['col1'].append(col1)   
    
    return(frames_props)
    

#TODO make this more efficient
def predict_frames(img, frames_props, predictor):
    """
    Predict frames.
    
    Args:
        img (array): Apeep image
        frames_props (dict): dict of frames label and coordinates
        predictor: Detectron2 model to use for prediction
    
    Returns:
        preds (dataframe): predictions found in image
    """
    ## Preprocess image for prediction
    # Apeep image is in range [0,1], change it to range [0, 255]
    # TODO make sure it's alsways the case to avoid useless computation
    if img.max() <= 1:
        img = img*255    
    # Apeep image has 1 channel, duplicate it to create a 3 channels image
    img = np.stack([img, img, img], axis=2)
    
    ## Initiate empty dict to store image predictions
    preds = {
        'frame_label': [],
        'frame_row': [],
        'frame_col': [],
        'score': [],      # prediction score
        'bbox': [],       # predicted bbox
        'bbox_corr': [],  # predicted bbox corrected for frame position in image
        'mask': [],       # predicted mask
    }
    
    ## Loop over frames to predict
    for i in range(len(frames_props['frame_label'])):
    
        # Extract frame labels
        frame_label = frames_props['frame_label'][i]
        frame_row = frames_props['frame_row'][i]
        frame_col = frames_props['frame_col'][i]
        
        # And coordinates
        row0 = int(frames_props['row0'][i]) # top row
        row1 = int(frames_props['row1'][i]) # bottom row
        col0 = int(frames_props['col0'][i]) # left column
        col1 = int(frames_props['col1'][i]) # right column
        
        # Extract frame from image
        frame = img[row0:row1, col0:col1, :]
        
        # Predict frame
        pred = predictor(frame)
        
        # If instances are detected, process them
        if len(pred['instances']) > 0:
            # Loop over prediction instances
            for idx in range(len(pred['instances'])):
                
                # Extract instance
                inst = pred['instances'][idx]
                
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


def resolve_overlaps(img_preds, overlap_threshold=0.2):
    """
    Resolve semantic prediction overlaps.
    
    1. Detect bbox overlaps -> potential overlaps
    2. Check mask overlaps -> true and false overlaps
    3. Process false overlaps
    3. Resolve true overlaps

    Args:
        img_preds (df): semantic predictions with frame and pred info
        overlap_threshold (float): mask iou between to predictions to consider an overlap. In range ]0,1]

    Returns:
        preds_ok (df): semantic predictions without overlapping predictions
    """
    
    ## Detect bbox overlaps to list potential overlaps
    # Initiate empty dict to store potential overlapping predictions 
    pot_overlaps = {
        'i': [],
        'j': [],
    }
    # Loop over predictions and test bbox overlap for each prediction pair
    for i in img_preds.index:
        for j in img_preds.index:
            if j > i:
                # Check bbox interception
                inter = check_bbox_overlap(
                    img_preds['bbox_corr'][i].tolist(), 
                    img_preds['bbox_corr'][j].tolist()
                )
                # In case of bbox interception, store prediction index
                if inter:
                    pot_overlaps['i'].append(i)
                    pot_overlaps['j'].append(j)

    # Convert to dataframe
    pot_overlaps = pd.DataFrame(pot_overlaps)
    # Add a column for overlap status
    pot_overlaps['same'] = False
    # And one to store bbox union of potential overlaps
    pot_overlaps['bbox_union'] = np.empty((len(pot_overlaps), 0)).tolist()

    # Create a new df with only non overlapping predictions
    preds_ok = img_preds[~img_preds.index.isin(np.unique(pot_overlaps[['i', 'j']]))].reset_index(drop = 'True')
    # Drop bbox and mask as we won't need these
    preds_ok = preds_ok.drop(['bbox', 'mask'], axis=1)
    
    ## Check mask overlap to distinct between true and false overlaps
    # Loop over potential overlaps
    for t in pot_overlaps.index:
        # Extract overlaping prediction indexes
        i = pot_overlaps.loc[t,'i']
        j = pot_overlaps.loc[t,'j']
        
        # Determine overlapping case between:
        # - case 1: frame 1 is the same as frame 2
        # - case 2: frame 1 is at left of frame 2
        # - case 3: frame 1 is on top of frame 2
        # - case 4: frame 1 is at top-left diagonal of frame 2
        # - case 5: frame 1 is at top-right diagonal of frame 2
        
        # Extract frames row and column indexes
        frame_row_i = img_preds['frame_row'][i]
        frame_col_i = img_preds['frame_col'][i]
        frame_row_j = img_preds['frame_row'][j]
        frame_col_j = img_preds['frame_col'][j]
        
        # Case 1:
        if (frame_col_i == frame_col_j) & (frame_row_i == frame_row_j):
            # Frame 1 is the same as frame 2
            # Extract masks of overlap area
            mask_over_i = img_preds['mask'][i]
            mask_over_j = img_preds['mask'][j]            
        
        # Case 2: 
        if (frame_col_i < frame_col_j) & (frame_row_i == frame_row_j):
            # Frame 1 is at left of frame 2
            # Extract masks of overlap area
            mask_over_i = img_preds['mask'][i][:, -144:-1]
            mask_over_j = img_preds['mask'][j][:, 0:143]
        
        # Case 3: 
        if (frame_col_i == frame_col_j) & (frame_row_i < frame_row_j):
            # Frame 1 is on top of frame 2
            # Extract masks of overlap area
            mask_over_i = img_preds['mask'][i][-144:-1, :]
            mask_over_j = img_preds['mask'][j][0:143,:]
            
        # Case 4:
        if (frame_col_i < frame_col_j) & (frame_row_i < frame_row_j):
            # Frame 1 is on top-left diagonal of frame 2
            # Extract masks of overlap area
            mask_over_i = img_preds['mask'][i][-144:-1, -144:-1]
            mask_over_j = img_preds['mask'][j][0:143,0:143]
            
        # Case 5:
        if (frame_col_i > frame_col_j) & (frame_row_i < frame_row_j):
            # Frame 1 is on top-right diagonal of frame 2
            # Extract masks of overlap area
            mask_over_i = img_preds['mask'][i][-144:-1, 0:143]
            mask_over_j = img_preds['mask'][j][0:143,-144:-1]
            
        # Compute mask intersection over union (iou)
        mask_inter = np.sum(np.logical_and(mask_over_i, mask_over_j))
        mask_union = np.sum(np.logical_or(mask_over_i, mask_over_j))
        iou = mask_inter / mask_union
        
        # If iou is higher than overlap threshold, consider it as an overlap
        if iou > overlap_threshold: # it's an overlap
            # Save it as a true overlap
            pot_overlaps.loc[t, 'same'] = True
            
            # Compute bbox union
            bbox_corr_i = img_preds['bbox_corr'][i].tolist()
            bbox_corr_j = img_preds['bbox_corr'][j].tolist()
            bbox_corr = compute_bbox_union(bbox_corr_i, bbox_corr_j)
            
            # And write bbox to df
            pot_overlaps.at[t, 'bbox_union'].extend(bbox_corr)

    ## Process false overlaps: store them with non overlapping predictions
    # Extract cases which are not overlaps
    not_overlaps = pot_overlaps[~pot_overlaps['same']]
    # List predictions which are not overlaps
    preds_not_overlaps = np.unique(not_overlaps[['i', 'j']])
    
    # Make sure these predictions do not overlap with other particles at some point
    preds = [] # initiate empty list to store preds which are not overlaps
    for pred in preds_not_overlaps: # loop over predictions which are supposed to not be overlaps
        over = pot_overlaps[(pot_overlaps['i'] == pred) | (pot_overlaps['j'] == pred)]['same'].any() # check if pred was associated with another overlap
        if not over: # if it was not, store it with non overlapping preds
            preds.append(pred) 
        
    # Loop over predictions and create entries for these
    for pred in preds:
        entry = {
            'frame_label': img_preds['frame_label'][pred],
            'frame_row': img_preds['frame_row'][pred],
            'frame_col': img_preds['frame_col'][pred],
            'score': img_preds['score'][pred],
            'bbox_corr': img_preds['bbox_corr'][pred],
            'pred_index': pred,
        }        
        # Store prediction with non overlapping predictions
        preds_ok = preds_ok.append(entry, ignore_index=True)
    
    ## Process cases of 1 big prediction encompassing 2 smaller ones which do not overlap: in this case we want to keep the two small ones
    # If masks of the two small predictions do not overlap, we can and we want to separate them
    all_large_preds = [] # initiate list to store large encompassing predictions
    for n in not_overlaps.index:
        # extract prediction indexes
        i = not_overlaps.loc[n, 'i']
        j = not_overlaps.loc[n, 'j']
        
        # We want overlaps that matches with both i and j  while i and j are NOT overlaps
        # predictions overlapping with i
        over_i = np.setdiff1d(np.unique(pot_overlaps[((pot_overlaps['i'] == i) | (pot_overlaps['j'] == i)) & (pot_overlaps['same'] == True)][['i', 'j']]), i)
        # predictions overlapping with j
        over_j = np.setdiff1d(np.unique(pot_overlaps[((pot_overlaps['i'] == j) | (pot_overlaps['j'] == j)) & (pot_overlaps['same'] == True)][['i', 'j']]), j)
        # predictions overlapping with both i and j
        large_preds = np.intersect1d(over_i, over_j).tolist() 
        all_large_preds.extend(large_preds) # add these predictions to the list of encompassing predictions
        
    all_large_preds = list(set(all_large_preds)) # make list unique
    
    # and finally ignore these large predictions by removing them from potentiel overlaps
    pot_overlaps = pot_overlaps[~((pot_overlaps['i'].isin(all_large_preds)) | (pot_overlaps['j'].isin(all_large_preds)))].reset_index(drop=True)
    
    ## Resolve cases wich are true overlaps
    # Extract cases which are true overlaps
    overlaps = pot_overlaps[pot_overlaps['same']]
    # Create a column for solving status and initiate it to False
    overlaps = overlaps.assign(solved = False)
    
    # Loop over true overlaps and process them
    for t in overlaps.index:
        
        # Check of overlap is already solved
        if not overlaps.loc[t, 'solved']:
            # If not solve, process it
            
            # First, determine if it's a simple or multiple overlap
            # Check how many times pred i and j appear in the dataframe
            i = overlaps.loc[t, 'i']
            j = overlaps.loc[t, 'j']
            
            # Number of times pred i was considered as an overlap
            nb_i = sum(overlaps['i'] == i) + sum(overlaps['j'] == i)
        
            # Number of times pred j was considered as an overlap
            nb_j = sum(overlaps['i'] == j) + sum(overlaps['j'] == j)
            
            # Case of simple overlap: both predictions are only once in overlaps
            if (nb_i == 1) and (nb_j == 1):
                # Prepare new entry for df of non overlapping predictions
                # Keep info of first frame for label, frame row and column
                # Compute average of score
                # Use newly computed bbox_corr
                entry = {
                    'frame_label': img_preds['frame_label'][i],
                    'frame_row': img_preds['frame_row'][i],
                    'frame_col': img_preds['frame_col'][i],
                    'score': np.mean([(img_preds['score'][i], img_preds['score'][j])]),
                    'bbox_corr': overlaps['bbox_union'][t],
                    'pred_index': i,
                }  
                
                # Store prediction with non overlapping predictions
                preds_ok = preds_ok.append(entry, ignore_index=True)
                
                # Set overlap as solved
                overlaps.loc[t, 'solved'] = True
                    
            # Case of multiple overlap
            else:
                # Extract all cases of overlaps
                cases = overlaps[(overlaps['i'].isin([i,j])) | (overlaps['j'].isin([i,j]))]
                # NB: some overlap cases might not be detected at first, e.g. in the case of pred i in top-left frame, overlap between top-right and bottom left is missed. 
                # Include missed cases
                # List indexes of included predictions
                cases_indexes = np.unique(cases[['i', 'j']])
                # Look for other rows with these predictions
                all_cases = overlaps[(overlaps['i'].isin(cases_indexes)) | (overlaps['j'].isin(cases_indexes))]
                
                # Extract bboxes
                bboxes = all_cases['bbox_union'].tolist()
                
                # TODO extract scores
                
                # Sequentially compute union of all bboxes
                bbox_union = bboxes[0]
                for r in range(len(bboxes)-1):
                    bbox_union = compute_bbox_union(
                        bbox_union, 
                        bboxes[r+1],
                    )  
                
                # Keep 1st prediction but with bbox_union and averaged score     
                # Prepare new entry for df of non overlapping predictions
                # Keep info of first frame for label, frame row and column
                # Compute average of score
                # Use newly computed bbox_corr
                entry = {
                    'frame_label': img_preds['frame_label'][i],
                    'frame_row': img_preds['frame_row'][i],
                    'frame_col': img_preds['frame_col'][i],
                    'score': np.mean([(img_preds['score'][i], img_preds['score'][j])]),
                    'bbox_corr': bbox_union,
                    'pred_index': i,
                }        
                # Store prediction with non overlapping predictions
                preds_ok = preds_ok.append(entry, ignore_index=True)
                
                # Set overlaps as solved
                overlaps.loc[all_cases.index, 'solved'] = True
    
    return(preds_ok)


def extract_rois(img, preds, dilate=2):
    """
    Extract image backgound of bbox predictions by semantic segmentation model. 
    Return a blank image with only background of ROIs.

    Args:
        img (array): image 
        preds(df): predictions from Detectron2
        dilate (int): number of pixels to grow particles and bboxes with (dilation). 

    Returns:
        img_rois (array): white image with background for predicted bbox only 
    """
    # Get image dimensions
    h, w = img.shape
    
    # Initiate new image with white background
    img_rois = np.ones_like(img)
    
    # Loop over predictions and paste image bbox content
    for i in preds.index:
        
        # Get bbox
        bbox = preds.loc[i, 'bbox_corr']
        
        # Extract bbox content slice with `dilate` extra px on each side so particle can be dilated
        # Make sure that slice do not cross images borders
        slice_bbox = (
            slice(max(0, bbox[1]-dilate), min(h, bbox[3]+dilate)), 
            slice(max(0, bbox[0]-dilate), min(w, bbox[2]+dilate))
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
        inter (bool): TRUE if there is an intersection, FALSE if not
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
    bbox_union(list): coordinates of bbox union as [x1, y1, x2, y2]
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
        mask (array): labelled merged image mask 
    """
    ## Compute mask overlap
    mask = np.logical_or(semantic_mask > 0, regular_mask > 0)
            
    ## Label particles
    mask_labelled = skimage.measure.label(mask, background=False, connectivity=2)
    regions = skimage.measure.regionprops(mask_labelled)
    
    mask_labelled_unique = np.zeros_like(mask_labelled) # initiate empty mask for new labels
    
    # create list of odd numbers for labels to avoid multiple particles with identical labels
    # If one particle is located inside another one, the sum of their label is an even number, different from every other label.
    n_regions = len(regions)
    labels = range(1, n_regions*2+1, 2)
    # Replace labels in mask
    for i in range(n_regions):
        r = regions[i]
        mask_labelled_unique[r._slice] = mask_labelled_unique[r._slice] + labels[i]*r.filled_image
    
    return(mask_labelled_unique)