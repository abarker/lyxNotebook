
Lyx Notebook is a program which allows the word processor Lyx to be used as a
code-evaluating notebook (similar to Mathematica notebooks or the Sage
notebook).  

Only Linux is currently supported.

UPDATE, Mar. 2020
=================

Many improvements to the code have recently been made.  The GUI looks nicer
now, and a config file ``lyxnotebook.cfg`` with user-modifiable settings is now
written to the Lyx user dir.

Lyx Notebook has recently been updated to install with ``setup.py`` and
``pip``.  This creates the entry point script ``lyxnotebook`` (and another
one which works when called from a Lyx lfun bound to F12 by default).  The
older installation methods no longer work.  To install for development,
goto the root directory of the project and run::

   pip3 install -e . --user

For non-development use the ``-e`` option is not needed.  Inside a
virtualenv the ``--user`` option is not needed.  The ``tkinter`` module is
also required.  If it is not already installed, you can install it
on Ubuntu with::

   sudo apt install python3-tk

Now for Lyx 2.3 run this command and follow the instructions it gives::
   
   lyxnotebook --install --no-editable-insets

For Lyx 2.4 you can leave out the ``--no-editable-insets`` part.  To use
a Lyx user directory other than the default, use the ``--user-dir`` option
to set the path.

To uninstall the program, use ``pip uninstall lyxnotebook``.  Reset the bind
file to its previous value.  Delete the Lyx Notebook ``.module`` files
and ``.bind`` files in the ``.lyx`` directory.

Note that Lyx 2.4.0 may provide a mechanism to improve the program and
eliminate the currently-necessary inserting of magic-cookie strings to get
cell text.  The current development is targeted at that, but Lyx 2.0.3
also still works.

Earlier info
============

Lyx Notebook only works with interactive, interpreted languages.  The
currently-supported languages are Python 2, Python 3, Sage, Scala, R, and Bash.
There are custom insets for code cells and output cells.  When a cell is
evaluated the output is sent to the output cell.  The program keeps interpreter
processes running, maintaining their state.  The Listings package is used to
highlight the code in the code cells in the Latex-formatted printable output.

See the file ``doc/lyxNotebookDocs.pdf`` for an overview, details of the install
procedure, descriptions of all the available commands, and customization
options.  There are example Lyx files in the examples directory.

This program only works on Linux systems, and has only been tested recently on
Ubuntu distributions.  Most of the testing has been with Python 2 code cells.

Licensed under the MIT license.

