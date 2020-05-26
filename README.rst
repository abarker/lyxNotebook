
LyX Notebook is a program which allows the word processor LyX to be used as a
code-evaluating notebook (similar to Mathematica notebooks, the Sage
notebook, or Jupyter notebooks).  

Only Linux is currently supported.

UPDATE, May 2020
================

The code has been under further development.  Some changes other than general
code cleanup and are listed below.  The install method is still the same as in
the March update.

* A code cell will automatically write into a math inset if that inset
  immediately follows the code inset.  It will not create such an inset,
  though, the user needs to do that.  This allows, for example, having
  SymPy code print out Latex math equations which will then be rendered
  as a Lyx preview and will appear in the final document.

* The module running external interpreters now uses the Pexpect package by
  default, replacing the earlier hand-rolled version.  (This might make
  a Windows port possible, if wexpect works and process control issues
  are dealt with.)

UPDATE, Mar. 2020
=================

Many improvements to the code have recently been made.

* The GUI looks nicer now, using PySimpleGUI.
  
* A config file ``lyxnotebook.cfg`` with user-modifiable settings is now
  written to the LyX user dir.

* LyX 2.4.0 may provide a mechanism to improve the program and eliminate the
  currently-necessary inserting of magic-cookie strings to get cell text.  The
  current development is targeted at that, but LyX 2.0.3 also still works.

New install procedure
---------------------

LyX Notebook has recently been updated to install with ``setup.py`` and
``pip``.  This creates the entry point script ``lyxnotebook`` (and another
one which works when called from a LyX lfun bound to F12 by default).  The
older installation methods no longer work.  To install for development,
goto the root directory of the project and run::

   pip3 install -e . --user

For non-development use the ``-e`` option is not needed.  Inside a
virtualenv the ``--user`` option is not needed.  The ``tkinter`` module is
also required.  If it is not already installed, you can install it
on Ubuntu with::

   sudo apt install python3-tk

Now for LyX 2.3 run this command and follow the instructions it gives::
   
   lyxnotebook --install --no-editable-insets

For LyX 2.4 you can leave out the ``--no-editable-insets`` part.  To use
a LyX user directory other than the default, use the ``--user-dir`` option
to set the path.

To uninstall the program, use ``pip uninstall lyxnotebook``.  Reset the bind
file to its previous value.  Delete the LyX Notebook ``.module`` files
and ``.bind`` files in the ``.lyx`` directory.

Running and using
-----------------

Many of the details are still only documented in the older PDF manual at
https://github.com/abarker/lyxNotebook/blob/master/doc/lyxNotebookDocs.pdf

After installing, and for each document, insert the modules for the kinds
of cells that you want to use (e.g., Python or Python2).  Insert the
a code cell into the document and write some code into it.

You can then hit F-12 to start up Lyx Notebook, and hit F-1 to see a menu of
options.  The menu shows the available key bindings, also.

If something gets messed up, use undo to revert it.  Use caution with batch
cell update commands since ordinary undo cannot undo those operations and they
might no longer be working correctly (there is a save file and an option to
revert, though).

Earlier info
============

LyX Notebook only works with interactive, interpreted languages.  The
currently-supported languages are Python 2, Python 3, Sage, Scala, R, and Bash.
There are custom insets for code cells and output cells.  When a cell is
evaluated the output is sent to the output cell.  The program keeps interpreter
processes running, maintaining their state.  The Listings package is used to
highlight the code in the code cells in the Latex-formatted printable output.

See the file ``doc/lyxNotebookDocs.pdf`` for an overview, details of the install
procedure, descriptions of all the available commands, and customization
options.  There are example LyX files in the examples directory.

This program only works on Linux systems, and has only been tested recently on
Ubuntu distributions.  Most of the testing has been with Python 2 code cells.

Licensed under the MIT license.

