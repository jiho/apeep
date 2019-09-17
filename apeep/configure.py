import os
import logging
import pkg_resources

import yaml

def config(project_dir):
    """
    Configure apeep options

    Args:
        project_dir (str): path to the project directory
    
    Returns:
        dict: settings in key-value pairs
    """
    # get general logger
    log = logging.getLogger()

    log.debug("Read apeep default configuration")
    defaults_file = pkg_resources.resource_filename("apeep", "config.yaml")
    with open(defaults_file, 'r') as ymlfile:
        defaults_cfg = yaml.safe_load(ymlfile)

    project_cfg_file = os.path.join(project_dir, "config.yaml")
    if os.path.exists(project_cfg_file):
        log.debug("Read this project's configuration file")
        with open(project_cfg_file, 'r') as ymlfile:
            project_cfg = yaml.safe_load(ymlfile)
            # when the file is empty, the return value is None, not an empty dict
            if project_cfg is None:
                project_cfg = {}
    else:
        project_cfg = {}

    log.debug("Combine defaults and project-level settings")
    # settings in the project's config will update those in the defaults
    # settings missing in the project's config will be kept at their default values (and added to the project's config after writing the file back)
    cfg = defaults_cfg.copy()
    cfg.update(project_cfg)
    # TODO perform a left join rather than this, to remove obsolete keys in project_cfg


    log.debug("Write updated configuration file")
    # change yaml dictionnary writer to preserve the order of the input dictionnary instead of sorting it alphabetically
    # https://stackoverflow.com/questions/16782112/can-pyyaml-dump-dict-items-in-non-alphabetical-order
    yaml.add_representer(dict, lambda self, data: yaml.representer.SafeRepresenter.represent_dict(self, data.items()))
    with open(project_cfg_file, 'w') as ymlfile:
        yaml.dump(cfg, ymlfile, default_flow_style=False)

    return(cfg)
