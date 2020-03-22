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
    args = parser.parse_args()

    if args.install:
        from . import install
        install.run_setup("lyxnotebook-from-lfun") # Pass lfun script name to set up a key binding.

    else:
        from . import run_lyxnotebook
        run_lyxnotebook.main()


def run_lyxnotebook_from_LFUN():
    """Run LyxNotebook from a Lyx LFUN.  This requires associating it with a terminal
    if it is not already associated with one."""
    from . import run_lyxnotebook_from_LFUN
    run_lyxnotebook_from_LFUN.main("lyxnotebook") # Pass regular script name to call after setup.

