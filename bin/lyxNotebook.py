"""

Run the program.


"""

import os
import sys
import argparse

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, "..", "src"))

import lyxNotebook

parser = argparse.ArgumentParser()
parser.add_argument("--LFUN", action="store_true", help="Run from a Lyx LFUN.")
parser.add_argument("--install", action="store_true", help=
                    "Install files in the Lyx directory specified in user_settings file.")
args = parser.parse_args()

if args.install:
    from lyxNotebook import install
    install.run_setup()

elif args.LFUN:
    from lyxNotebook import lyxNotebookFromLFUN
    lyxNotebookFromLFUN.main()

else:
    from lyxNotebook import run_lyxNotebook
    run_lyxNotebook.main()


