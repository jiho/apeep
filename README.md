
# apeep

`apeep` is a suite of tools to process images produced by the In Situ Ichthyoplankton Imaging System ([ISIIS](http://yyy.rsmas.miami.edu/groups/larval-fish/isiis.html)).

It is mostly written in Python (a snake), is meant to deal is data form ISIIS (almost Isis, the Egyptian deity) so it is called `apeep`, almost [Apep](http://en.wikipedia.org/wiki/Apep), an Egyptian deity which takes the form of a giant snake ;)


# Installation

Tested with Python 2.7, not with Python >= 3 because opencv bindings are hard to get working


## Python packages

pip install numpy
pip install scipy
pip install six
pip install -U scikit-image
pip install matplotlib
pip install python-dateutil


## Install dependencies

### OS X

    brew install opencv

### Linux

    sudo apt-get install python-opencv

On Ubuntu 14.04 at least, opencv crashes when reading videos. It needs to be compiled from source with ffmpeg switched off and replaced by gstreamer

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
    cmake -D CMAKE_BUILD_TYPE=Release -D CMAKE_INSTALL_PREFIX=/usr/local -D WITH_V4L=OFF -D WITH_FFMPEG=OFF -D WITH_GSTREAMER=ON ..

    # build (on 6 cores) and install
    make -j 6
    sudo make install
    


