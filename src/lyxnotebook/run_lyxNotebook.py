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

This program should always be run from the Lyx Notebook source directory, so it
can find the path to that directory.  The variable
`lyxNotebook_user_settings.lyx_notebook_source_dir` is dynamically set to the
argv[0] directory of this command.  Use a short stub shell-script to call it
from the source directory if you want a version in, say `~/bin`.

"""

import os
import sys
import time
from . import lyxNotebook_user_settings # before controller_lyx_with_interpreter, dynamic vars set

# Get the Lyx Notebook home directory.  Some interpreters may use this if they
# store data in the auxiliaryFilesForInterpreters directory, so the value is
# stored as an on-the-fly calculated variable in the lyxNotebook_user_settings
# namespace.

lyx_notebook_source_dir = os.path.dirname(__file__)
lyxNotebook_user_settings.lyx_notebook_source_dir = lyx_notebook_source_dir
os.chdir(lyx_notebook_source_dir) # Makes relatives paths work in user_settings.

# Do below import *after* the calculations above, since implicitly import process_interpreter_specs
from .controller_of_lyx_and_interpreters import ControllerOfLyxAndInterpreters

# Set the lockfile location to be in the user's local Lyx directory.
user_home_lyx_directory = lyxNotebook_user_settings.user_home_lyx_directory
lockfile_path = os.path.abspath(os.path.expanduser(
    os.path.join(user_home_lyx_directory, "lyxNotebook.lockfile")))

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
            print("You already have an instance of LyX Notebook running.")
            print("It is running as process", old_PID + ".  Exiting.")
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
          lyxNotebook_user_settings.lyx_notebook_source_dir)

    controller = ControllerOfLyxAndInterpreters("lyxNotebookClient")
    controller.server_notify_loop()


