import os
import logging
import pkg_resources
import sys

import yaml

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
    cfg = defaults_cfg.copy()
    cfg.update(project_cfg)
    # TODO perform a left join rather than this, to remove obsolete keys in project_cfg

    # check correctedness of configuration values
    if not cfg['acq']['top'] in ("right", "left") :
        log.error("`acq > top` should be 'right' or 'left'")
        sys.exit(1)
    if not isinstance(cfg['acq']['scan_per_s'], (int, float)) :
        log.error("`acq > scan_per_s` should be a number")
        sys.exit(1)

    if not isinstance(cfg['flat_field']['window_size'], (int, float)) :
        log.error("`flat_field > window_size` should be a number")
        sys.exit(1)
    if not isinstance(cfg['flat_field']['step_size'], (int, float)) :
        log.error("`flat_field > step_size` should be a number")
        sys.exit(1)

    if not isinstance(cfg['process']['image_size'], (int, float)) :
        log.error("`process > image_size` should be a number")
        sys.exit(1)

    if ( cfg['process']['light_threshold'] < 0. ) or \
       ( cfg['process']['light_threshold'] > 100. ) :
        log.error("`process > light_threshold` should be in [0,100] (0, no change; 100, clip to white)")
        sys.exit(1)
  
    if not cfg['segment']['dark_threshold_method'] in ("dynamic", "static") :
        log.error("`process > dark_threshold_method` should be 'dynamic' or 'static'")
        sys.exit(1)
    if ( cfg['segment']['dark_threshold'] < 0. ) or \
       ( cfg['segment']['dark_threshold'] > 100. ) :
        log.error("`segment > dark_threshold` should be in [0,100] (0, no particles; 100, select everything)")
        sys.exit(1)

    if not isinstance(cfg['segment']['dilate'], (int, float)) :
        log.error("`segment > dilate` should be a number")
        sys.exit(1)
    
    # TODO: check all settings
    
    # add the configuration to the log
    log.info(cfg)

    log.debug("write updated configuration file")
    # change yaml dictionnary writer to preserve the order of the input dictionnary instead of sorting it alphabetically
    # https://stackoverflow.com/questions/16782112/can-pyyaml-dump-dict-items-in-non-alphabetical-order
    yaml.add_representer(dict, lambda self, data: yaml.representer.SafeRepresenter.represent_dict(self, data.items()))

    with open(project_cfg_file, 'w') as ymlfile:
        yaml.dump(cfg, ymlfile, default_flow_style=False)

    return(cfg)
