"""

=========================================================================
This file is part of LyX Notebook, which works with LyX but is an
independent project.  License details (MIT) can be found in the file
COPYING.

Copyright (c) 2012 Allen Barker
=========================================================================

Read and return values from the config file.

"""

import configparser
import os
from . import gui_elements

# All config data is flattened into this single dict, ignoring sections.
config_dict = {}

config_parser = configparser.ConfigParser()

lyx_notebook_source_dir = os.path.abspath(os.path.dirname(__file__))
config_dict["lyx_notebook_source_dir"] = lyx_notebook_source_dir

def to_bool(cfg_value):
    """Convert config file booleans to Python booleans."""
    if cfg_value in {"0", "false", "False", "no"}:
        return False
    if cfg_value in {"1", "true", "True", "yes"}:
        return True
    raise ValueError("Value {} in config file must be boolean in"
                     " a form such as 0/1, true/false, yes/no."""
                     .format(cfg_value))

def initialize_config_data():
    """Initialize the data dict `config_dict` from the config file at
    the path `config_file_path`.  Flattened into a single dict with
    quotes stripped off of everything, booleans converted to bool, and
    ints converted to ints."""
    find_and_load_config_file(config_parser)

    for section in config_parser.sections():
        subdict = dict(config_parser[section])
        config_dict.update(subdict)

    for key, value in config_dict.items():
        config_dict[key] = value.strip("'")
        config_dict[key] = value.strip('"')

    bool_settings = [
        "always_start_new_terminal",
        "no_echo",
        "buffer_replace_on_batch_eval",
        "separate_interpreters_for_each_buffer",
        "has_inset_edit_noeditor_mod",
        "has_inset_edit",
        ]

    for setting in bool_settings:
        config_dict[setting] = to_bool(config_dict[setting])

    int_settings = [
        "max_lines_in_output_cell",
        "num_backup_buffer_copies",
        ]

    for setting in int_settings:
        config_dict[setting] = int(config_dict[setting])


def find_and_load_config_file(config_parser):
    """Search for a relevant config file, and load it into `config_file`."""
    # Default on linux should be ~/.config/lyxnotebook dir,  the XDG
    # standard.   Maybe just make that dir and put it there...
    #
    # For portability, consider this way to find a dir:
    # https://github.com/ActiveState/appdirsa
    #
    # How jupyter does it: https://jupyter.readthedocs.io/en/latest/projects/jupyter-directories.html
    #
    # Currently just searches on a path...
    homedir = os.path.expanduser("~")

    config_search_path = [
                          os.path.join(homedir, ".config"),
                          os.path.join(homedir, "lyxnotebook", ".config"),
                          homedir,
                          os.environ.get("LYXNOTEBOOK_CONF"),
                          os.path.join(homedir, ".lyx")
                          ]

    found_config = False
    for dirname in config_search_path:
        if not dirname:
            continue
        pathname = os.path.join(dirname, "lyxnotebook.cfg")
        for filename in ["lyxnotebook.cfg", ".lyxnotebook.cfg"]:
            try:
                with open(pathname) as cfgfile:
                    config_parser.read(cfgfile)
                found_config = True
            except IOError:
                pass

    if not found_config:
        msg = "\nWarning: Could not find config file 'lyxnotebook.cfg', using default values."
        print(msg)
        pathname = os.path.join(lyx_notebook_source_dir,
                                    "default_config_file_and_data_files",
                                    "default_config_file.cfg")
        config_parser.read(pathname)

    print("\nFound and loaded config file at:\n   ", pathname)

# Just loading this module initializes the config.  We need the config data
# when running from command line or from lfun, i.e., from different modules.
initialize_config_data()

# General config parser reminder examples.
#print(config_data.sections())
#config_data.options('magic cookie')
#config_data.get('magic cookie', 'magic_cookie_string')
#config_data.get('magic cookie', 'magic_cookie_string')
#config_data['magic cookie'].getboolean('magic_cookie_string')
#config_data['magic cookie']['magic_cookie_string']

