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

# All config data is flattened into this single dict, ignoring sections.
config_dict = {}

config_parser = configparser.ConfigParser()


def to_bool(cfg_value):
    """Convert config file booleans to Python booleans."""
    if cfg_value in {"0", "false", "no"}:
        return False
    if cfg_value in {"1", "true", "yes"}:
        return True
    raise ValueError("Value {} in config file must be boolean in"
                     " a form such as 0/1, true/false, yes/no."""
                     .format(cfg_value))

def initialize_config_data():
    """Initialize the data dict `config_dict` from the config file at
    the path `config_file_path`.  Flattened into a single dict with
    quotes stripped off of everything, booleans converted to bool, and
    ints converted to ints."""

    lyx_notebook_source_dir = os.path.abspath(os.path.dirname(__file__))
    config_dict["lyx_notebook_source_dir"] = lyx_notebook_source_dir

    config_file_path = os.path.join(lyx_notebook_source_dir, # TODO: Search locations, see below.
                                    "default_config_file.ini")

    if not os.path.isfile(config_file_path):
        raise IOError("Config file '{}' does not exist.".format(config_file_path))
    config_parser.read(config_file_path)

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

initialize_config_data()

def find_and_load_config_file():
    """Search for a relevant config file, and load it."""
    # TODO

    # Default on linux should be ~/.config/lyxnotebook dir,  the XDG
    # standard.   Maybe just make that dir and put it there...
    #
    # For portability, consider this way to find:
    # https://github.com/ActiveState/appdirsa
    #
    # How jupyter does it: https://jupyter.readthedocs.io/en/latest/projects/jupyter-directories.html

    home_dir = os.path.expanduser("~")

    config_search_path = [os.curdir,
                          os.path.expanduser("~"),
                          os.environ.get("LYXNOTEBOOK_CONF")]

    for dirname in config_search_path:
        try:
            with open(os.path.join(dirname, "lyxnotebook.cfg")) as cfgfile:
                config_parser.read(cfgfile)
            found_config = True
        except IOError:
            pass

#initialize_config_data("default_config_file.ini")
#print(config_dict)

# General config parser reminder examples.
#print(config_data.sections())
#config_data.options('magic cookie')
#config_data.get('magic cookie', 'magic_cookie_string')
#config_data.get('magic cookie', 'magic_cookie_string')
#config_data['magic cookie'].getboolean('magic_cookie_string')
#config_data['magic cookie']['magic_cookie_string']

