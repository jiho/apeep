def checkmakedirs(path) :
    """
    Check the accessibility of a directory and create it if it does not exist
    
    path : string
        path to the directory to be checked/created
        intermediate directories will be created if needed
    """
    import os
    from tempfile import mkstemp
    import errno

    # try to create the directory(ies)
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            # do not warn if the directory already exists
            raise
    
    # try writing to the directory
    try:
        f_descriptor, f_name = mkstemp(dir=path)
    except:
        raise
    os.close(f_descriptor)
    os.remove(f_name)
