import glob
import datetime
import scipy
import pandas as pd
import numpy as np
#from ipdb import set_trace as db

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
    start = head[1][6:14] + " " + e['Time'][min(e.index)]
    start = datetime.datetime.strptime(start, "%m/%d/%y %H:%M:%S.%f")
    
    # compute the time steps between each record in the file
    # NB: repeat the first time to get a start step of 0
    times = list(e['Time'])
    times.insert(0, e['Time'][min(e.index)])
    # then compute the deltas
    steps = np.diff([datetime.datetime.strptime(t, "%H:%M:%S.%f") for t in times])
    # deal with crossing midnight
    steps = np.where(steps < datetime.timedelta(seconds=0), steps + datetime.timedelta(days=1), steps)
    
    # now compute date_time using cumulated time since start
    e['Date Time'] = start + np.cumsum(steps)

    # clean column names
    # import re
    # [re.sub("[ \(\)\.\/]", "_", k).lower().replace("°", "deg").replace("__", "_") for k in e.keys()]

    # rename env dataframe columns 
    #e = e.rename(columns=lambda x: x.split("..")[0].replace('.', '_').replace(' ', '_').lower())
    e = e.rename(columns=lambda x: x.lower().split(" (")[0].split("..")[0].replace('. ', ' ').replace('.', ' ').replace(' ', '_').replace('long', 'lon'))
    e.columns =  "object_" + e.columns

    # drop time column
    e = e.drop('object_time', axis=1)
    
    # smooth depth, keep only 2 decimals
    e['object_depth'] = [round(x, 2) for x in smooth(e['object_depth'], k = 10, n = 5)]
    
    # compute cast number
    # find peaks indexes
    peaks, _ =  scipy.signal.find_peaks(e.object_depth, width = 100, distance = 1000)
    
    # find pits indexes
    pits, _ = scipy.signal.find_peaks(e.object_depth * (-1), width = 100, distance = 1000)
    
    # set all peaks and pits to False
    e['peaks'] = False
    e['pits'] = False
    
    # set to True at indexes of peaks and pits
    e.loc[peaks, 'peaks'] = True
    e.loc[pits, 'pits'] = True
    
    # compute cast as cumulative sum of peaks or pits + 1
    sample_ids = np.cumsum(np.logical_or(e.pits, e.peaks)) + 1
    
    # find transect name and type to write sample_id as lagXX_yoYY, ccXX_yoYY or acXX_yoYY
    transect_name = path.split("/")[-2] # should be something like: Lagrangian_XX, Cross-current_XX or Along-current_XX
    transect_nb = transect_name.split("_")[-1]
    if "lagrangian" in transect_name.lower():
        transect_type = "lag"
    elif "cross" in transect_name.lower():
        transect_type = "cc"
    elif "along" in transect_name.lower():
        transect_type = "ac"
    else:
        transect_type = ""
    
    e['sample_id'] = [transect_type + transect_nb + "_yo" + str(s).zfill(2) for s in sample_ids]
    
    # drop peaks and pits
    e = e.drop(["peaks", "pits"], axis=1)
    
    # split object_depth to object_depth_min and object_depth_max
    e = e.rename(columns={"object_depth": "object_depth_min"})
    e['object_depth_max'] = e['object_depth_min']
    
    ## Reorder columns
    # columns to move at the beginning
    cols_to_order = ["sample_id",
                     "object_depth_min",
                     "object_depth_max"]
    new_columns = cols_to_order + (e.drop(cols_to_order, axis = 1).columns.tolist())
    e = e[new_columns]  
    
    return(e)
    

def merge_environ(env, parts, name):
    """
    Join enviromental and particles data based on datetime. Return an ecotaxa compatible dataframe ready to be written as a tsv. 
    
    Args:
        env (DataFrame): dataframe with environmental data and ecotaxa formats as first row
        parts (DataFrame): dataframe with particles properties data and ecotaxa formats as first row
        name (str): name of destination directory
    
    Returns:
        (DataFrame) with environmental and particles data, proper columns names and formats as first row
    """
    
    # if environmental data is available, proceed to join with parts data
    if len(env.index) > 0:
        # convert date_time to datetime
        env['object_date_time'] = pd.to_datetime(env['object_date_time'], format="%Y-%m-%d %H:%M:%S.%f")
        
        ## Join
        # fuzzy join by datetime to nearest, with 1s tolerance
        parts = pd.merge_asof(parts.sort_values("object_date_time"), env.sort_values("object_date_time"),
                      left_on="object_date_time", right_on="object_date_time", direction="nearest", 
                      tolerance=pd.Timedelta('5s'))
        
        # drop obj_date_time (joining) column
        parts = parts.drop('object_date_time', axis=1)

        ## Reorder columns
        # columns to move at the beginning
        cols_to_order = [
            "img_file_name",
            "object_id",
            "object_label",
            "sample_id",
            "acq_id",
            "object_date",
            "object_time",
            "object_lat",
            "object_lon",
            "object_depth_min",
            "object_depth_max"
        ]
        new_columns = cols_to_order + (parts.drop(cols_to_order, axis = 1).columns.tolist())
        parts = parts[new_columns]
        
    # if no environmental data available
    else:
        # delete useless object_date_time column
        parts = parts.drop('object_date_time', axis = 1)
        
        # reorder columns
        cols_to_order = [
            "img_file_name",
            "object_id",
            "object_label",
            "acq_id",
            "object_date",
            "object_time"
        ]
        new_columns = cols_to_order + (parts.drop(cols_to_order, axis = 1).columns.tolist())
        parts = parts[new_columns]
        
    return(parts)

    
    
def smooth(x, k=1, n=1):
    """
    Smooth a variable in a cast using a weighted moving average. 
    
    Args:
        x : vector to smooth
        k (int) : order of the window
        n (int) : number of times to smooth the data
    
    Returns:
        (list) with the smoothed data
    """
    
    # make sure that x is a list
    if type(x)!=list:
        x = x.tolist()
        
    # repeat n times
    for t in range(1,n):
        
    # pad the extremities of data to be able to compute over the whole vector
        x = np.insert(x, 0, [np.nan]*k)
        x = np.append(x, [np.nan]*k)
        
        # compute centered weights
        w = list(range(1, k+1, 1)) + [k+1] + list(range(k, 0, -1))
        
        # Run weighted average on sliding window, ignoring nan values
        x = [np.average(np.ma.MaskedArray(np.take(x, range(i-k, i+k+1, 1)), 
                                          mask=np.isnan(np.take(x, range(i-k, i+k+1, 1)))),
                        weights=np.ma.MaskedArray(w, mask=np.isnan(np.take(x, range(i-k, i+k+1, 1))))) 
             for i in range(k, len(x)-k)]
        
    return(x)