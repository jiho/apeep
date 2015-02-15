
def view(x, interactive=True):
    """quick function to show a grey level image"""
    from matplotlib import pyplot as p
    from pylab import cm
    if interactive:
        p.ion()
    else:
        p.ioff()
    p.imshow(x, cmap=cm.gray, interpolation='nearest')
