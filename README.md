
# apeep

`apeep` is a set of tools to process images produced by the In Situ Ichthyoplankton Imaging System ([ISIIS](http://yyy.rsmas.miami.edu/groups/larval-fish/isiis.html)).

It is mostly written in Python (a snake), is meant to deal is data form ISIIS (almost [Isis](http://en.wikipedia.org/wiki/Isis), the Egyptian deity) so it is called `apeep`, almost [Apep](http://en.wikipedia.org/wiki/Apep), an Egyptian deity which takes the form of a giant snake! And it is supposed to churn through your data without a peep, of course. (Yes, finding the name took longer than coding the thing...)


## Installation

Install external libraries needed by `apeep` and/or the packages it depends on

    sudo apt install cmake pkg-config libavcodec-dev libavformat-dev libavdevice-dev libavutil-dev libpng-dev libjpeg-dev 
    
Install `pip` for python 3 (usually called `pip3`)

    sudo apt install python3-pip

Install `apeep` from this repository

    pip3 install git+https://github.com/jiho/apeep

This should install other python packages `apeep` depends on. 

If you install as a regular user, `apeep` installs in `~/.local/` and you need to make sure that `~/.local/bin` is in your `PATH` to be able to run it. Typically, this is done by editing `~/.bashrc` and writing

    export PATH="~/.local/bin:${PATH}"

If you install with `sudo pip3 ...` then `apeep` should be installed in `/usr/local` and should already be in your `PATH`.

# Usage

`apeep` takes `.avi` files from ISIIS, flat-fields them with a moving average, increases the contrasts of the resulting image, detects objects and extracts them, together with some measurements of each individual object. Typically, it is run as a command line tool.

`apeep` has the concept of **project**. A project is simply a directory containing a configuration file, `apeep`'s logs and its output (full processed frames, segmented objects, etc.). To create a project, simply run

    apeep /path/to/project

`apeep` will create the project directory and then instruct you to edit the configuration file. The configuration file (called `config.yaml`) is a simple text file that sets various options for `apeep`. These options are documented [here](https://github.com/jiho/apeep/blob/master/apeep/config.yaml).

The first important option to set is the path to the directory containing the **input** `.avi` files. This can be within the project directory (then everything is self contained) but, because the input data is often very large, this is frequently a directory elsewhere, on another drive.

Once the options are set (at least the path to the input directory), re-run the same project with `apeep` and it should start processing the data

    apeep /path/to/project


## Development

To change `apeep`'s code, clone this repository, edit the code, and run the *local* version of the package rather than the pip-installed one

    git clone https://github.com/jiho/apeep.git
    cd apeep
    # edit what you need to edit, then
    python3 -m apeep --debug /path/to/project

To test new code, it is useful to have a dedicated test project. A repository with test files is available. To use it

    wget https://github.com/jiho/apeep_test/archive/master.zip
    unzip master.zip
    python3 -m apeep apeep_test-master/out

When developing new functionality, it is often useful to place one self in a given context (inside a function, within the main loop, etc.). To stop execution at any point and jump into a python interpreter, uncomment the line

    # from ipdb import set_trace as db

at the beginning of the file of interest and write `db()` at the point at which you want to stop in the file. You will enter python interactive debugger (the prompt is `ipdb>`). You can run code there and all variables present at this point in the execution are available to work with. The only limitation is that `ipdb` will not execute multiline statements. Do do so, within `ipdb`, type `interact` which opens a temporary interactive python session. Exit it (with `CTRL+D`) and you will fall back into the `ipdb` session.


## Credits

ISIIS is developed by [Robert K Cowen](http://ceoas.oregonstate.edu/profile/cowen/) ([Rosenstiel School of Marine and Atmospheric Sciences](http://www.rsmas.miami.edu/) RSMAS, University of Miami and [Hatfield Marine Science Center](http://hmsc.oregonstate.edu), Oregon State University) and [Cédric Guigand](https://people.miami.edu/profile/c.guigand@miami.edu) ([RSMAS](http://www.rsmas.miami.edu)) in partnership with [BellaMare](http://www.bellamare-us.com).

`apeep` is coded by [Jean-Olivier Irisson](http://www.obs-vlfr.fr/~irisson/) ([Laboratoire d'Océanographie de Villefranche](http://lov.obs-vlfr.fr) LOV) and released under the [GNU General Public License v3](http://www.gnu.org/copyleft/gpl.html).
