import logging
import os
import datetime

# from ipdb import set_trace as db

def log(project_dir, debug=False):
    log = logging.getLogger()

    # define the output format for log messages
    log_formatter = logging.Formatter("%(asctime)s.%(msecs)03d : %(levelname)s : %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    
    # log to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    log.addHandler(console_handler)
    
    # log to file
    log_dir = os.path.join(project_dir, "log")
    log_file = os.path.join(log_dir, datetime.datetime.now().strftime("log_%Y-%m-%d_%H-%M-%S.txt"))
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(log_formatter)
    log.addHandler(file_handler)

   # define log level
    if debug:
        log_level = logging.DEBUG
    else :
        log_level = logging.INFO
    log.setLevel(log_level)

    return(log)
