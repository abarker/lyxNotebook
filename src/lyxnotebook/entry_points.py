"""

These are the entry points to run LyxNotebook.  They are set up in `setup.py`
to become command-line commands.

"""

import os
import sys
import argparse

script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)

def run_lyxnotebook():
    """Run LyxNotebook in the ordinary way from a terminal."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true", help=
                  "Install files in the Lyx directory specified in user_settings file.")
    parser.add_argument("--cfg-path", nargs=1, help=
                        "Pass in the path to the config file to use.")
    args = parser.parse_args()

    if args.cfg_path:
        print("------------> GOT AN ARG in main run_lyxnotebook...", args.cfg_path[0])

    # TODO: Modify the install script to be able to take an install-dir argument.
    # See the bind file in the current .lyx test dir.... be sure to backslash quote the *whole*
    # command and args passed in the actual LFUN.
    #
    # Need to pass another argument to install.run_setup if installing, to install the
    # bind file with the correct --bind-dir argument.
    #
    # In normal run the config data must have the passed-in setting, so IMPORT config module
    # here, and pass it the argument.  Use it if passed in, otherwise search path.

    if args.install:
        from . import install
        install.run_setup("lyxnotebook-from-lfun") # Pass lfun script name to set up a key binding.

    else:
        from . import run_lyxnotebook
        run_lyxnotebook.main()


def run_lyxnotebook_from_LFUN():
    """Run LyxNotebook from a Lyx LFUN.  This requires associating it with a terminal
    if it is not already associated with one."""
    # Todo: later maybe make this another command-line option of the main entry point.
    parser = argparse.ArgumentParser()
    parser.add_argument("--cfg-path", nargs=1, help=
                        "Pass in the path to the config file to use.")
    args = parser.parse_args()

    print("sys.args is", sys.argv)
    cmd = "lyxnotebook"
    if args.cfg_path:
        cmd += " --cfg-path '{}'".format(args.cfg_path[0])
        print("GOT ARG from LFUN!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", args.cfg_path)

    from . import run_lyxnotebook_from_LFUN
    run_lyxnotebook_from_LFUN.main(cmd) # Pass regular script name to call after setup.

