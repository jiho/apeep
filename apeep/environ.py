import glob
import datetime

import pandas as pd
import numpy as np

def read_environ(path):
    """
    Read a text file containing environmental data collected by ISIIS
    
    Args:
        path (str): path to the file
    
    Returns:
        (DataFrame) with the content of the file
    """
    
    # read the header to parse the date
    with open(path, encoding="latin1") as f:
        head = [next(f) for i in range(10)]
    
    # read the content
    e = pd.read_csv(path, sep="\t", skiprows=10, encoding="latin1", header=0, na_values=["NA", "NaN", "No GPS Data"])
    # NB: content only has times, not date+time
    
    # add a datetime column
    # parse the start date and time
    start = head[1][6:14] + " " + e['Time'][0]
    start = datetime.datetime.strptime(start, "%m/%d/%y %H:%M:%S.%f")
    
    # compute the time steps between each record in the file
    # NB: repeat the first time to get a start step of 0
    times = list(e['Time'])
    times.insert(0, e['Time'][0])
    # then compute the deltas
    steps = np.diff([datetime.datetime.strptime(t, "%H:%M:%S.%f") for t in times])
    # deal with crossing midnight
    steps = np.where(steps < datetime.timedelta(seconds=0), steps + datetime.timedelta(days=1), steps)
    
    # now compute date_time using cumulated time since start
    e['Date Time'] = start + np.cumsum(steps)

    # clean column names
    # import re
    # [re.sub("[ \(\)\.\/]", "_", k).lower().replace("°", "deg").replace("__", "_") for k in e.keys()]

    return(e)
