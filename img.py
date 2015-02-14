
def view(x):
    """quick function to show a grey level image"""
    from matplotlib import pyplot as p
    from pylab import cm
    p.ion()
    p.imshow(x, cmap=cm.gray, interpolation='nearest')
