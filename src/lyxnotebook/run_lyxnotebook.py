#! /usr/bin/python
"""

=========================================================================
This file is part of LyX Notebook, which works with LyX but is an
independent project.  License details (MIT) can be found in the file
COPYING.

Copyright (c) 2012 Allen Barker
=========================================================================

This script runs the Lyx Notebook program.  It mainly checks to make sure
that there is no other active Lyx Notebook process running, and if not then
it launches an instance of the main `ControllerOfLyxAndInterpreters` class.

"""

import os
import sys
import time
from .config_file_processing import config_dict
from .controller_of_lyx_and_interpreters import ControllerOfLyxAndInterpreters
from . import gui

lyx_user_directory = config_dict["lyx_user_directory"]
lockfile_path = os.path.abspath(os.path.expanduser(
                   os.path.join(lyx_user_directory, "lyxNotebook.lockfile")))

def main():
    """
    Make sure this script is not already running in an existing process.
    This method uses a lock file containing the PID, and was modified from code at
    http://shoaibmir.wordpress.com/2009/12/14/pid-lock-file-in-python/
    """
    # First check if a lock file already exists.
    if os.path.exists(lockfile_path):
        # If the lockfile is already there then check the PID number in the lock file.
        pidfile = open(lockfile_path, "r")
        pidfile.seek(0)
        old_PID = pidfile.readline()
        # Check if the PID from the lock file matches the current process PID.
        if os.path.exists(os.path.join("/proc", old_PID)):
            msg = ("You already have an instance of LyX Notebook running."
                   "\nIt is running as process {}.  Exiting.".format(old_PID))
            print(msg)
            gui.text_info_popup(msg)
            time.sleep(4) # For when a new terminal opened, so message can be read.
            sys.exit(1)
        else:
            # Lock file exists but the program is not running... remove it.
            os.remove(lockfile_path)

    # Put the current PID in the lock file.
    pidfile = open(lockfile_path, "w")
    pidfile.write(str(os.getpid()))
    pidfile.close()

    #
    # Start the main controller class.
    #

    print("\n===================================================\n")
    print("Starting the LyX Notebook program...")
    print("Version from source directory:\n   ",
          config_dict["lyx_notebook_source_dir"])

    controller = ControllerOfLyxAndInterpreters("lyxNotebookClient")
    controller.server_notify_loop()


