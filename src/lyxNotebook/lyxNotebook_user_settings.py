# -*- coding: utf-8 -*-
"""

User-modifiable settings for the Lyx Notebook program.

"""


# ===============================================================================
# Pathnames also set in Lyx.  These must match whatever the Lyx program uses.
# They are initially set to the Lyx default values.
# ===============================================================================


# The LyX user home directory.
user_home_lyx_directory = "~/.lyx"
user_home_lyx_directory = "~/programming/python/lyxNotebook/project_root/test/.lyx"
#user_home_lyx_directory = "~/.lyx-2.1.0svn"
#user_home_lyx_directory = "~/.lyx-2.0.4svn"

# This setting must match: Tools->Preferences->Paths->LyXServerPipe
lyx_server_pipe = "~/.lyx/lyxpipe"
import os
lyx_server_pipe = os.path.join(user_home_lyx_directory, "lyxpipe")
#lyx_server_pipe = "~/.lyx-2.1.0svn/lyxpipe"
#lyx_server_pipe = "~/.lyx-2.0.4svn/lyxpipe"

# This setting should match: Tools->Preferences->Paths->TemporaryDirectory
lyx_temporary_directory = "/tmp"


# ===============================================================================
# General settings.
# ===============================================================================


# The maximum number of lines written to an output cell (before truncation).
max_lines_in_output_cell = 1000

# The LyX process name in the "ps -f" output (basename only).
# Setting to a "wrong" value which no process uses will cause LyX Notebook
# to open an xterm for output rather than sending output to the same
# terminal as the running LyX process.
lyx_command_string = "lyx"
#lyx_command_string = "lyx-2.1.0svn"
#lyx_command_string = "lyx-2.0.4svn"

# Whether to always start a new terminal window for Lyx Notebook output.
# This only applies when the program is run as lyxNotebookFromLFUN.py, such
# as when it is run from inside Lyx.
always_start_new_terminal = False

# Default initial value for echoing mode in output cells.
no_echo = True

# Default initial setting of whether to replace and reload the buffer after
# a batch evaluation, or whether to open the file as a new buffer.
buffer_replace_on_batch_eval = False

# The number of saved copies of replaced buffers in the evaluation commands
# which replace the current buffer.
num_backup_buffer_copies = 5

# The cookie string which is temporarily inserted.  Only alphanumeric
# strings have been tested.  Definitely cannot contain a semicolon.
magic_cookie_string = "zZ3Qq"
magic_cookie_string = "œ" # Ligature OE (Latin).
magic_cookie_string = "»" # Right-pointing double angle quotation mark.
magic_cookie_string = "»»" # Right-pointing double angle quotation mark.

# Whether Lyx Notebook should start up separate interpreter processes for the same
# cell types in different buffers.
separate_interpreters_for_each_buffer = True


# ===============================================================================
# Values calculated on-the-fly by the program, saved and shared in this namespace.
# ===============================================================================


# The source directory of the Lyx Notebook program, where the command lyxNotebook
# lives (the directory is calculated in that command's code, from argv[0]).
lyx_notebook_source_dir = "__dummy__"

