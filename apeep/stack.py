import os

import numpy as np
from PIL import Image
from pytoshop.user import nested_layers
import pytoshop.enums as pse

import apeep.timers as t

# from ipdb import set_trace as db

@t.timer
def save_stack(img, labels, dest, format=['rgb', 'tif', 'psd']):
    # get image size
    nrow, ncol = img.shape
    
    # RGB image where the mask is red
    if 'rgb' in format:    
        masked = np.zeros((nrow, ncol, 3), dtype="uint8")
        masked[:,:,0] = (img * 254 + 1) * (labels != 0)  # R
        masked[:,:,1] = (img * 254 + 1) * (labels == 0)  # G
        masked[:,:,2] = masked[:,:,1]                  # B
        # NB: shift of 1 from the background to be able to easily re-extract the mask
        # save to file
        masked_img = Image.fromarray(masked)
        masked_img.save(dest + ".png")

    # multilayer, coloured TIFF file
    if 'tif' in format:
        # create background as RGB
        back = np.zeros((nrow, ncol, 3), dtype="uint8")
        back[:,:,0] = img * 255
        back[:,:,1] = back[:,:,0]
        back[:,:,2] = back[:,:,0]
        back_img = Image.fromarray(back)
        # create mask as RGBA
        mask = np.zeros((img_size, img_width, 4), dtype="uint8")
        mask[:,:,0] = (labels != 0) * 255
        mask[:,:,3] = mask[:,:,0]
        mask_img = Image.fromarray(mask)
        # save as multipage TIFF
        back_img.save(dest + ".tif", format="tiff", append_images=[mask_img], save_all=True, compression='tiff_lzw')

    # multilayer Photoshop file
    if 'psd' in format:
        blank = np.zeros((nrow, ncol), dtype="uint8")
        # create background as RGB
        back = (img*255).astype(np.uint8)
        back_dict = {
            0: back, # R
            1: back, # G
            2: back  # B
        }
        # create mask as RGBA
        mask = ((labels != 0) * 255).astype(np.uint8)
        mask_dict = {
            0 : mask,  # R
            1 : blank, # G
            2 : blank, # B
            -1: mask   # A
        }
        # combine background and semi transparent mask
        back_layer = nested_layers.Image(name="back", channels=back_dict, \
            opacity=255, color_mode=pse.ColorMode['rgb'])
        mask_layer = nested_layers.Image(name="mask", channels=mask_dict, \
            opacity=150, color_mode=pse.ColorMode['rgb'])
        psd = nested_layers.nested_layers_to_psd([mask_layer, back_layer],   \
            color_mode=pse.ColorMode['rgb'], depth=pse.ColorDepth['depth8'], \
            compression=pse.Compression['rle'])
        # write inside a subdirectory to make post-processing in external sofware easier
        os.makedirs(dest, exist_ok=True)
        psd.write(open(os.path.join(dest, "frame.psd"), "wb"))
        # TODO use with

        pass