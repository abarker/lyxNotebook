# This is the bashrc file which is used for the bash shells in Lyx Notebook.
# The file first sources the usual .bashrc file, if it exists, so those
# settings are used.  Then, however, it redefines the prompt strings.  This
# is to provide Lyx Notebook with consistent and predictable prompts which
# do not depend on, say, the current directory.

echo "Loading lyxNotebookBashrc, with reliable prompt pattern..."

RCFILE="/etc/bash.bashrc"
#RCFILE="~/.bashrc"

if [ -r "$RCFILE" ]; then
   source "$RCFILE"
else
   echo "Startup bashrc file nonexistent or unreadable..."
fi

export PS1='bash $ '
export PS2='bash > '
export PS3='bash > '

