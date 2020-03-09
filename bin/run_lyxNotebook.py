#!/usr/bin/python3
"""

Run the program.


"""

import os
import sys
import argparse

script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
sys.path.insert(0, os.path.join(script_dir, "..", "src"))

import lyxNotebook

def run_from_lfun():
    from lyxNotebook import lyxNotebookFromLFUN
    lyxNotebookFromLFUN.main(script_path)

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true", help=
                        "Install files in the Lyx directory specified in user_settings file.")
    args = parser.parse_args()

    if args.install:
        from lyxNotebook import install
        install.run_setup(os.path.join(script_dir, "run_lyxNotebook_from_LFUN.py"))

    else:
        from lyxNotebook import run_lyxNotebook
        run_lyxNotebook.main()

