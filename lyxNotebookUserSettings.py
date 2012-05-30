
"""
User-modifiable settings for the Lyx Notebook program.
"""

# ===============================================================================
# General settings.
# ===============================================================================

# The maximum number of lines written to an output cell (before truncation).
maxLinesInOutputCell = 1000 

# The LyX process name in the "ps -eo command" output (basename only).
# Setting to a "wrong" value which no process uses will cause LyX Notebook 
# to always open an xterm for output rather than sending output to the same 
# terminal as the running LyX process.
lyxCommandString = "lyx"
#lyxCommandString = "lyx-2.1.0svn"

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

# ===============================================================================
# Pathnames also set in Lyx.  These must match whatever the Lyx program uses.
# They are initially set to the Lyx default values.
# ===============================================================================

# The LyX user home directory.
userHomeLyxDirectory = "~/.lyx"
#userHomeLyxDirectory = "~/.lyx-2.1.0svn"

# This should be the same as: Tools->Preferences->Paths->LyXServerPipe 
lyxServerPipe = "~/.lyx/lyxpipe"
#lyxServerPipe = "~/.lyx-2.1.0svn/lyxpipe"

# This should be the same as: Tools->Preferences->Paths->TemporaryDirectory
lyxTemporaryDirectory = "/tmp"

