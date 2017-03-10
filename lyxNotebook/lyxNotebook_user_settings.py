# -*- coding: utf-8 -*-
"""

User-modifiable settings for the Lyx Notebook program.

"""


# ===============================================================================
# Pathnames also set in Lyx.  These must match whatever the Lyx program uses.
# They are initially set to the Lyx default values.
# ===============================================================================


# The LyX user home directory.
userHomeLyxDirectory = "~/.lyx"
#userHomeLyxDirectory = "~/.lyx-2.1.0svn"
#userHomeLyxDirectory = "~/.lyx-2.0.4svn"

# This setting must match: Tools->Preferences->Paths->LyXServerPipe
lyxServerPipe = "~/.lyx/lyxpipe"
#lyxServerPipe = "~/.lyx-2.1.0svn/lyxpipe"
#lyxServerPipe = "~/.lyx-2.0.4svn/lyxpipe"

# This setting should match: Tools->Preferences->Paths->TemporaryDirectory
lyxTemporaryDirectory = "/tmp"


# ===============================================================================
# General settings.
# ===============================================================================


# The maximum number of lines written to an output cell (before truncation).
maxLinesInOutputCell = 1000

# The LyX process name in the "ps -f" output (basename only).
# Setting to a "wrong" value which no process uses will cause LyX Notebook
# to open an xterm for output rather than sending output to the same
# terminal as the running LyX process.
lyxCommandString = "lyx"
#lyxCommandString = "lyx-2.1.0svn"
#lyxCommandString = "lyx-2.0.4svn"

# Whether to always start a new terminal window for Lyx Notebook output.
# This only applies when the program is run as lyxNotebookFromLFUN, such
# as when it is run from inside Lyx.
alwaysStartNewTerminal = False

# Default initial value for echoing mode in output cells.
noEcho = True

# Default initial setting of whether to replace and reload the buffer after
# a batch evaluation, or whether to open the file as a new buffer.
bufferReplaceOnBatchEval = False

# The number of saved copies of replaced buffers in the evaluation commands
# which replace the current buffer.
numBackupBufferCopies = 5

# The cookie string which is temporarily inserted.  Only alphanumeric
# strings have been tested.  Definitely cannot contain a semicolon.
magicCookieString = "zZ3Qq"

# Whether Lyx Notebook should start up separate interpreter processes for the same
# cell types in different buffers.
separateInterpretersForEachBuffer = True


# ===============================================================================
# Values calculated on-the-fly by the program, saved and shared in this namespace.
# ===============================================================================


# The source directory of the Lyx Notebook program, where the command lyxNotebook
# lives (the directory is calculated in that command's code, from argv[0]).
lyxNotebookSourceDir = "__dummy__"

