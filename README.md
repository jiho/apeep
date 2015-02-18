
# apeep

`apeep` is a set of tools to process images produced by the In Situ Ichthyoplankton Imaging System ([ISIIS](http://yyy.rsmas.miami.edu/groups/larval-fish/isiis.html)).

It is mostly written in Python (a snake), is meant to deal is data form ISIIS (almost Isis, the Egyptian deity) so it is called `apeep`, almost [Apep](http://en.wikipedia.org/wiki/Apep), an Egyptian deity which takes the form of a giant snake! (Yes, finding the name took longer than coding the thing...)


# Installation

Tested with Python 2.7, not with Python >= 3 because opencv bindings are hard to get working. The image reading and writing is done through [Open CV](http://opencv.org "OpenCV | OpenCV") because it is fast, fast, fast.

## Python packages

[pip](https://pypi.python.org/pypi/pip) makes it easy. [Install it](https://pip.pypa.io/en/latest/installing.html) if you do not have it already. Then

    pip install numpy
    pip install scikit-image
    pip install matplotlib


## Open CV

### OS X

The easiest is via [Homebrew](http://brew.sh "Homebrew — The missing package manager for OS X"). Install homebrew:

    ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

and then

    brew install opencv

### Linux

Package managers have prebuilt python bindings. In Debian/Ubuntu:

    sudo apt-get install python-opencv

However, in Ubuntu 14.04 at least, Open CV crashes when reading videos. It needs to be compiled from source with ffmpeg switched off and replaced by gstreamer

    # install building tools
    sudo apt-get install build-essential
    sudo apt-get install cmake libgtk2.0-dev pkg-config libavcodec-dev libavformat-dev libswscale-dev
    
    # install additional functionality (for python bindings in particular)
    sudo apt-get install python-dev python-numpy libjpeg-dev libpng-dev libtiff-dev libtbb2 libtbb-dev \
                         libjasper-dev libdc1394-22-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
                         nvidia-cuda-dev
    
    # get source code
    wget http://sourceforge.net/projects/opencvlibrary/files/opencv-unix/2.4.10/opencv-2.4.10.zip
    unzip opencv-2.4.10.zip
    cd opencv-2.4.10

    # configure
    mkdir build
    cd build
    sudo ln -sf /usr/lib/nvidia-331-updates/libnvcuvid.so /usr/lib/libnvcuvid.so
    sudo ln -sf /usr/lib/nvidia-331-updates/libnvcuvid.so.1 /usr/lib/libnvcuvid.so.1
    cmake -D CMAKE_BUILD_TYPE=Release -D CMAKE_INSTALL_PREFIX=/usr/local -D WITH_V4L=OFF \
          -D WITH_FFMPEG=OFF -D WITH_GSTREAMER=ON ..

    # build (on 6 cores) and install
    make -j 6
    sudo make install


## Test installation

In a terminal type

    python

and then at the prompt

    import numpy
    import skimage
    import matplotlib
    import cv2

all this should work, with no warning.


# Usage

[Download](https://github.com/jiho/apeep/archive/master.zip) the code, unzip it, edit `process.py` to fit your configuration. At least the `input_dir` and `output_dir` variables need to be changed. Then run with

    ./process.py

At this point, the only documentation is reading the code itself. The variable names in `process.py` should be self-explanatory though.


