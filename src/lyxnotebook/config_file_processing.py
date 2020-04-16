"""

=========================================================================
This file is part of LyX Notebook, which works with LyX but is an
independent project.  License details (MIT) can be found in the file
COPYING.

Copyright (c) 2012 Allen Barker
=========================================================================

Read and return values from the config file.


General config parser reminder examples:

    print(config_data.sections())
    config_data.options('magic cookie')
    config_data.get('magic cookie', 'magic_cookie_string')
    config_data.get('magic cookie', 'magic_cookie_string')
    config_data['magic cookie'].getboolean('magic_cookie_string')
    config_data['magic cookie']['magic_cookie_string']

"""

import configparser
import os
#from . import gui

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

def initialize_config_data(lyx_user_dir):
    """Initialize the data dict `config_dict` from the config file at
    the path `config_file_path`.  Flattened into a single dict with
    quotes stripped off of everything, booleans converted to bool, and
    ints converted to ints."""
    print("\nInitializing config data for LyX user dir:\n   {}"
            .format(lyx_user_dir))
    cfg_file_name = os.path.join(lyx_user_dir, "lyxnotebook.cfg")

    try:
        with open(cfg_file_name) as cfgfile:
            pass # Configparser silently fails to load data with nonexistent file.
    except IOError:
        raise IOError("Cannot find file 'lyxnotebook.cfg' in the LyX user"
                " at this path\n   {}.".format(cfg_file_name))
    config_parser.read(cfg_file_name)

    print("\nFound and read the config file:\n   {}".format(cfg_file_name))

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
        "has_editable_insets_noeditor_mod",
        "has_editable_insets",
        "gui_window_always_on_top",
        ]

    for setting in bool_settings:
        config_dict[setting] = to_bool(config_dict[setting])

    int_settings = [
        "max_lines_in_output_cell",
        "num_backup_buffer_copies",
        ]

    for setting in int_settings:
        config_dict[setting] = int(config_dict[setting])

    config_dict["lyx_user_directory"] = lyx_user_dir



