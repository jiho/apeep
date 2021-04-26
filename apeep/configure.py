import os
import logging
import pkg_resources
import sys

import yaml
import numpy as np

#from ipdb import set_trace as db

def configure(project_dir):
    """
    Configure apeep options

    Args:
        project_dir (str): path to the project directory

    Returns:
        dict: settings in key-value pairs
    """
    # get general logger
    log = logging.getLogger()

    log.debug("read apeep default configuration")
    defaults_file = pkg_resources.resource_filename("apeep", "config.yaml")
    with open(defaults_file, 'r') as ymlfile:
        defaults_cfg = yaml.safe_load(ymlfile)

    project_cfg_file = os.path.join(project_dir, "config.yaml")
    if os.path.exists(project_cfg_file):
        log.debug("read this project's configuration file")
        with open(project_cfg_file, 'r') as ymlfile:
            project_cfg = yaml.safe_load(ymlfile)
            # when the file is empty, the return value is None, not an empty dict
            if project_cfg is None:
                project_cfg = {}
    else:
        project_cfg = {}

    log.debug("combine defaults and project-level settings")
    # settings in the project's config will update those in the defaults
    # settings missing in the project's config will be kept at their default values (and added to the project's config after writing the file back)
    cfg = left_join_dict(defaults_cfg, project_cfg)

    # check correctedness of configuration values
    log.debug("check configuration values")
    
    # NB: do not check io > input_dir existence here because it would fail by default

    assert cfg['acq']['top'] in ("right", "left"), \
            "`acq > top` should be either 'right' or 'left'"
    assert isinstance(cfg['acq']['scan_per_s'], (int, float)), \
            "`acq > scan_per_s` should be a number"
    assert isinstance(cfg['acq']['window_height_mm'], (int, float)), \
            "`acq > window_height_mm` should be a number"

    assert isinstance(cfg['subsampling']['interval'], (int)), \
            "`subsampling > interval` should be an integer"
    assert (cfg['subsampling']['interval'] > 0), \
            "`subsampling > interval` should be > 0"
    assert isinstance(cfg['subsampling']['first_image'], (int)), \
            "`subsampling > first_image` should be an integer"
    assert (cfg['subsampling']['first_image'] > 0), \
            "`subsampling > first_image` should be > 0"

    assert isinstance(cfg['flat_field']['window_size'], (int, float)), \
            "`flat_field > window_size` should be a number"
    assert isinstance(cfg['flat_field']['step_size'], (int, float)), \
            "`flat_field > step_size` should be a number"
    step = closest_power_of_two(cfg['flat_field']['step_size'])
    if step != cfg['flat_field']['step_size']:
        log.info("`flat_field > step_size` updated to " + str(step))
    cfg['flat_field']['step_size'] = step
    window_size = make_divisible(cfg['flat_field']['window_size'], by=step)
    if window_size != cfg['flat_field']['window_size']:
        log.info("`flat_field > window_size` updated to " + str(window_size))
    cfg['flat_field']['window_size'] = window_size

    assert isinstance(cfg['enhance']['image_size'], (int, float)), \
            "`enhance > image_size` should be a number"
    image_size = make_divisible(cfg['enhance']['image_size'], by=step)
    if image_size != cfg['enhance']['image_size']:
        log.info("`enhance > image_size` updated to " + str(image_size))
    cfg['enhance']['image_size'] = image_size
    assert isinstance(cfg['enhance']['dark_threshold'], (int, float)), \
            "`enhance > dark_threshold` should be a number"
    assert (cfg['enhance']['dark_threshold'] >= 0 and \
            cfg['enhance']['dark_threshold'] <= 100), \
            "`enhance > dark_threshold` should be in [0,100]"
    assert isinstance(cfg['enhance']['light_threshold'], (int, float)), \
            "`enhance > light_threshold` should be a number"
    assert (cfg['enhance']['light_threshold'] >= 0 and \
            cfg['enhance']['light_threshold'] <= 100), \
            "`enhance > light_threshold` should be in [0,100]"
    assert (cfg['enhance']['dark_threshold'] <= cfg['enhance']['light_threshold']), \
            "`enhance > dark_threshold` should be smaller than `enhance > light_threshold`"
    
    assert isin(cfg['segment']['stack_format'], ("psd", "tif", "rgb")), \
            "`segment > stack_format` can only be 'psd', 'tif', 'rgb'"
    assert cfg['segment']['pipeline'] in ("semantic", "regular", "both"), \
            "`segment > pipeline` can only be 'semantic', 'regular', 'both'" 
    assert (cfg['segment']['sem_conf_threshold'] >= 0 and \
            cfg['segment']['sem_conf_threshold'] <= 1), \
            "`segment > sem_conf_threshold` should be in [0,1]"
    assert isinstance(cfg['segment']['sem_min_area'], (int, float)), \
            "`segment > sem_min_area` should be an number"
    assert isinstance(cfg['segment']['sem_max_area'], (int, float)), \
            "`segment > sem_max_area` should be an number"
    assert cfg['segment']['sem_min_area'] < cfg['segment']['sem_max_area'], \
            "`segment > sem_min_area` should smaller than `segment > sem_max_area`"
    assert cfg['segment']['method'] in ("static", "percentile", "otsu", "auto"), \
            "`segment > method` should be 'static', 'percentile', 'otsu' or 'auto'"
    assert isinstance(cfg['segment']['threshold'], (int, float)), \
            "`segment > threshold` should be a number"
    assert (cfg['segment']['threshold'] >= 0 and \
            cfg['segment']['threshold'] <= 100), \
            "`segment > threshold` should be in [0,100] (0, no particles; 100, select everything)"
    assert isinstance(cfg['segment']['var_limit'], (int, float)), \
            "`segment > var_limit` should be a number"
    assert isinstance(cfg['segment']['dilate'], (int)), \
            "`segment > dilate` should be an number"
    assert isinstance(cfg['segment']['erode'], (int)), \
            "`segment > erode` should be an number"            
    assert isinstance(cfg['segment']['reg_min_area'], (int, float)), \
            "`segment > reg_min_area` should be an number"
    assert isinstance(cfg['segment']['reg_max_area'], (int, float)), \
            "`segment > reg_max_area` should be an number"
    assert cfg['segment']['reg_min_area'] < cfg['segment']['reg_max_area'], \
            "`segment > reg_min_area` should smaller than `segment > reg_max_area`"
    
    # TODO check boolean values

    # add the configuration to the log
    log.info(cfg)

    log.debug("write updated configuration file")
    # change yaml dictionnary writer to preserve the order of the input dictionnary instead of sorting it alphabetically
    # https://stackoverflow.com/questions/16782112/can-pyyaml-dump-dict-items-in-non-alphabetical-order
    yaml.add_representer(dict, lambda self, data: yaml.representer.SafeRepresenter.represent_dict(self, data.items()))

    with open(project_cfg_file, 'w') as ymlfile:
        yaml.dump(cfg, ymlfile, default_flow_style=False)

    return cfg

def closest_power_of_two(x):
    x = int(x)
    if x == 1:
        o = x
    else:
        # see https://codereview.stackexchange.com/questions/105911/largest-power-of-two-less-than-n-in-python
        # for the clever bit switching part
        under = 1 << (x.bit_length() - 1)
        over  = 2 << (x.bit_length() - 1)
        # find which is closest
        i = np.argmin((x - under, over - x))
        o = (under, over)[i]
    return o

def make_divisible(x, by=1):
    return round(x / by) * by

def left_join_dict(x, y):
    """
    Recursive left join of dictionnaries.
    
    Any element of y whose key is in x will update the value from x.
    Any element of y that does not exists in x is ommited.
    Inspired from https://gist.github.com/angstwad/bf22d1822c38a92ec0a9

    Args:
        x (dict): reference dictionnary
        y (dict): dictionnary to be merged in x
    
    Returns:
        (dict) a new dictionnary.
    """
    # make a copy of the reference dict
    x = x.copy()
    # remove elements from y that are not in x
    y = { k: y[k] for k in set(x).intersection(set(y)) }
    # for each element of y
    for k,v in y.items():
        # if dict, iterate
        if isinstance(x.get(k), dict) and isinstance(v, dict):
            x[k] = left_join_dict(x[k], v)
        # if not, update
        else:
            x[k] = v
    return(x)

def isin(x, choices):
    """
    Check that the elements of x are all among choices
    
    Args
        x (list, tuple, etc.): the elements to check
        choices (list, tuple, etc.): the possibilities
        
    Returns:
        (bool) True if all elements of x are in choices, False otherwise
    """
    diff = set(x) - set(choices)
    return(len(diff) == 0)
 