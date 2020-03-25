"""

These are the entry points to run LyxNotebook.  They are set up in `setup.py`
to become command-line commands.

"""

import os
import sys
import argparse
from . import config_file_processing

script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)

def parse_args():
    """Parse the command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true", help=
            "Install files in the LyX user directory specified by the '--user-dir'"
            " argument, if one is given.  By default files are installed in '~/.lyx'.")
    parser.add_argument("--no-editable-insets", action="store_true", help=
            "Whether or not the LyX version has editable insets (4.0 or greater)."
            " Needed to generate the layout module files since a new, incompatible,"
            " property was added (EditExternal).  Only meaningful with '--install';"
            " otherwise use the setting in the 'lyxnotebook.cfg' file.")
    parser.add_argument("--user-dir", nargs=1, help=
            "The LyX user directory in which to find or install LyX Notebook layout and"
            " binding files and the 'lyxnotebook.cfg' config file.  The default is"
            " '~/.lyx'.")
    parser.add_argument("--ensure-tty", action="store_true", help=
            "Passed to run LyX Notebook from a LyX LFUN, or any other situation where "
            "there is no obvious tty to associate with LyX Notebook.  This checks first, "
            "and opens a new tty if necessary.  (Running the interpreters requires a tty "
            "to be associated with them, and the LyX needs a place to write its stdout.)")
    args = parser.parse_args()
    return args


def run_lyxnotebook():
    """Run LyxNotebook in the ordinary way from a terminal."""
    args = parse_args()

    lyx_user_dir = args.user_dir[0] if args.user_dir else "~/.lyx"
    lyx_user_dir = os.path.abspath(os.path.expanduser(lyx_user_dir))

    if args.install:
        from . import install
        # Pass lfun script command to set up a key binding.
        install.run_setup(lyx_user_dir, "\\\"lyxnotebook --ensure-tty --user-dir {}\\\"".format(lyx_user_dir),
                has_editable_insets=not args.no_editable_insets)
        return

    from . import config_file_processing
    config_file_processing.initialize_config_data(lyx_user_dir)

    if args.ensure_tty:
        cmd_string = "lyxnotebook " + " ".join(sys.argv[1:])
        cmd_string = cmd_string.replace(" --ensure-tty", "") # Avoid recursive call.
        print("\nCommand to associate with a terminal: ", cmd_string)

        from . import run_lyxnotebook_from_LFUN
        run_lyxnotebook_from_LFUN.main(cmd_string) # Pass regular script name to call after setup.

    else:
        config_file_processing.initialize_config_data(lyx_user_dir)
        from . import run_lyxnotebook
        run_lyxnotebook.main()


