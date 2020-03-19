"""
=========================================================================
This file is part of LyX Notebook, which works with LyX but is an
independent project.  License details (MIT) can be found in the file
COPYING.

Copyright (c) 2012 Allen Barker
=========================================================================

Python will not run the lyxnotebook program correctly unless it has stdout
associated with some tty.  So we have to make that happen.

The Lyx Notebook program can be started in one of three ways.  It can 1) be run
from the command line in a terminal, 2) be run from a Lyx process which was run
from the command line in a terminal, or 3) be run from a Lyx process which was
run from an icon or a menu.  (We assume that Lyx Notebook is not run directly
from an icon or menu, but that shouldn't actually affect anything.)

We have three cases to deal with.  First, either the running "self" process is
associated with a terminal (this script was run from the command line) or it
is not (this script was run from a Lyx LFUN).  In the latter case we need to
associate the Lyx notebook process with SOME tty, and we have two different
subcases.  Either the user's running Lyx process is associated with a tty (it
was run from a command line) or it is not (it was run from the start menu or
an icon).  In the first subcase we use the tty for the running Lyx process, and
in the latter case we run the program in a new terminal window.

"""

# TODO: Results are different under Python3 and Python2 for some reason...

# TODO: Consider if using the sys.stdin.isatty() function would be helpful, and
# similarly for sys.stdout.isatty().  sys.stdin and sys.stdout are file objects.
# https://docs.python.org/2.4/lib/bltin-file-objects.html
#
# Consider also using psutil or a similar program to get running-program info.
# https://github.com/giampaolo/psutil

import subprocess
# import time
import os
import sys
import platform
from . import lyxNotebook_user_settings

python_version = platform.python_version_tuple()

# The lyx_command_string should match whatever Lyx runs as when the command "ps -f"
# is run.  If this process is not found then an xterm will be opened (so setting
# this to some "wrong" string will force an xterm to open rather than using the
# Lyx process' tty for writing output).
lyx_command_string = lyxNotebook_user_settings.lyx_command_string
always_start_new_terminal = lyxNotebook_user_settings.always_start_new_terminal

# Get path of the source dir from calling command for this script.
lyx_notebook_source_dir = os.path.dirname(__file__)
os.chdir(lyx_notebook_source_dir) # Make relative paths work in user_settings file.

my_PID = os.getpid()
my_CWD = os.getcwd()
operating_system_platform = sys.platform

# Utility function to get command output, for portability and future development.

def get_command_output(command_and_arg_list):
    """Return the output of the passed-in command."""
    print("\nPROCESS CALL:", " ".join(command_and_arg_list))
    output = subprocess.check_output(command_and_arg_list).decode("utf-8")
    print("OUTPUT:\n", output)
    return output

def main(script_run_command):
    """Set up so that the program has a TTY associated with it.  The
    `script_run_command` parameter should be the passed path to the script to
    run LyxNotebook normally (in order to run as a process after a TTY is
    detected or set up). The normal command is usually the entry point
    `lyxnotebook`."""

    #
    # Call the tty command to see if it returns a terminal.  Note that it will
    # fail if current "self" process was started via a Lyx LFUN call.  (The ps
    # output can give a tty even in that case, but we need to differentiate
    # since to work correctly when called from inside Lyx the stdout and
    # stderr must be explicitly redirected to a terminal.)
    #

    try:
        tty_command_output = get_command_output(["tty"]).strip()
    except:
        # If tty command fails, assume there is no associated tty and set
        # output the same as the output of the tty command when no tty.
        print("\nException in tty command, assuming 'not a tty' as the response.")
        tty_command_output = "not a tty"

    #
    # If the tty command found a tty, just start up the program normally.
    #

    if tty_command_output != "not a tty" and not always_start_new_terminal:
        print("Running LyX Notebook from terminal %s returned by tty command."
              % tty_command_output)
        try:
            subprocess.call(script_run_command, shell=True)
        except:
            sys.exit(1)
        sys.exit(0)

    #
    # No tty identified yet; parse the output of the ps command to find a tty.
    # Use "ps -f" and parse according to labels on the first line (for
    # portability to Cygwin).
    #

    process_data = get_command_output(["ps", "-f"])
    process_data = process_data.splitlines()

    column_labels = process_data[0].split()
    for i in range(len(column_labels)):
        if column_labels[i].strip() == "PID": pid_col = i
        if column_labels[i].strip() == "UID": uid_col = i
        if column_labels[i].strip() == "CMD": cmd_col = i
        if column_labels[i].strip() == "TTY": tty_col = i
    del process_data[0] # Remove the first line of the output, with column labels.

    # Go through process_data to find user ID and TTY for the current "self" process.
    # Also, delete all but the basename in the CMD column.
    for i in range(len(process_data)):
        process_data[i] = process_data[i].split()
        pid = int(process_data[i][pid_col].strip())
        if pid == my_PID:
            # Note the tty can be set in ps even if the tty command earlier failed.
            my_tty = process_data[i][tty_col].strip()
            # Get user of the current running "self" process.
            my_USER = process_data[i][uid_col].strip()
        process_data[i][cmd_col] = os.path.basename(process_data[i][cmd_col]) # only base

    #
    # Find the tty associated with Lyx, or create one with xterm if that fails.
    #

    # Make a sublist containing only the Lyx processes.
    my_lyx_procs = [p for p in process_data
                  if p[cmd_col] == lyx_command_string and p[uid_col] == my_USER]

    if len(my_lyx_procs) == 0:
        print("No terminal found and no Lyx process running, trying an xterm anyway.")
    if len(my_lyx_procs) > 1:
        print("Multiple Lyx processes running, trying an xterm anyway.")

    # Make a further sublist containing only the Lyx processes with terminals.
    my_lyx_procs_with_terminals = [p for p in my_lyx_procs if p[tty_col] != "?"]

    # Try opening ttys to select only a user-accessible one
    # (su to another user inside a terminal causes a fail, for example)

    def tty_is_writeable(tty_name):
        """Test to see if the tty `tty_name` can be opened for writing."""
        return os.access(tty_name, os.W_OK)

    my_lyx_procs_with_writeable_terminals = []
    for p in my_lyx_procs_with_terminals:
        tty_name = "/dev/" + p[tty_col]
        if tty_is_writeable(tty_name):
            my_lyx_procs_with_writeable_terminals.append(p)
        else:
            print("Rejecting terminal", tty_name, "since it is not user-accessible.")
            continue

    # See if we found a usable tty.  Prefer the my_tty one, for the "self" process.
    # Only use the process associated with "lyx" in the ps output if it is unique
    # (so we don't dump stuff to the wrong terminal).
    if my_tty != "?":
        terminal = "/dev/" + my_tty
        if tty_is_writeable(terminal):
            print("Sending output to the terminal associated with the "
                  + "lyxnotebook-from-lfun\n    process (should also be the Lyx "
                  + "process' terminal): " + terminal)
        elif len(my_lyx_procs_with_writeable_terminals) == 1: # unique Lyx terminal
            terminal = "/dev/" + my_lyx_procs_with_writeable_terminals[0][tty_col]
            print("Sending output to the terminal associated with the running\n"
                  + "    LyX process: " + terminal)
        else: terminal = "?" # none found, we'll need to start one
    else: terminal = "?" # none found, we'll need to start one

    # If a writeable terminal was found, use it, otherwise open an xterm window.
    if always_start_new_terminal or terminal == "?":
        if operating_system_platform.startswith("linux"):
            proc = subprocess.Popen(
                ["xterm -e 'cd {} ; {}'".format(my_CWD, script_run_command)],
                shell=True)
        else:
            pass # later add terminal for other platforms
    else: # got a unique terminal associated with current process or Lyx process
        proc = subprocess.Popen(["{} >{} 2>&1".format(script_run_command, terminal)], shell=True)

