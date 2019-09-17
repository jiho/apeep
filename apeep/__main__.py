# Implement console script as in
# https://www.geeksforgeeks.org/command-line-scripts-python-packaging/

# initialise logging and then each function just needs ot get_logger

import argparse
import os
import logging

import apeep


def main():
    # Parse command line arguments ----
    parser = argparse.ArgumentParser(
        prog="apeep",
        description="Process ISIIS data without a peep"
    )
  
    parser.add_argument("path", type=str, nargs=1,
        help="path to the project.")
    parser.add_argument("-d", "--debug", dest="debug", action="store_true",
        help="print debug messages.")

    args = parser.parse_args()
 
    # make sure project directory exists
    project_dir = args.path[0]
    os.makedirs(project_dir, exist_ok=True)
 
    # Setup logging ----
    log = apeep.log(project_dir, debug=args.debug)
    log.info("Start")
    log.debug("We're debugging!")

    # Read configuration file ----
    cfg = apeep.configure(project_dir)



if __name__ == "__main__":
    main()
