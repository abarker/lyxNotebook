# This is the bashrc file which is used for the bash shells in Lyx Notebook.
# The file first sources the usual .bashrc file, if it exists, so those
# settings are used.  Then, however, it redefines the prompt strings.  This
# is to provide Lyx Notebook with the consistent and predictable prompts
# to detect when output has finished.

echo
echo "Loading lyxNotebookBashrc, with a reliable prompt pattern..."
echo

RCFILE="/etc/bash.bashrc" # System bashrc is more replicable.
#RCFILE="~/.bashrc"

if [ -r "$RCFILE" ]; then
   source "$RCFILE"
else
   echo "Startup bashrc file is nonexistent or unreadable..."
fi

export PS1='bash $ '
export PS2='bash > '
export PS3='bash > '

