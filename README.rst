
Lyx Notebook is a program which allows the word processor Lyx to be used as a
code-evaluating notebook (similar to Mathematica notebooks or the Sage
notebook).  

UPDATE, Mar. 2020
=================

   Lyx Notebook has recently been updated to install with ``setup.py`` and
   ``pip``.  It then creates the entry point script ``lyxnotebook`` and another
   one which works when called from a Lyx lfun bound to F12 by default.  The
   older installation methods no longer work.  To install for development,
   goto the root directory of the project and run::

      pip install -e . --user

   For non-development use the ``-e`` option is not needed.  Inside a virtualenv
   the ``--user`` option is not needed.  Then type::
      
      lyxnotebook --install

   The program has only recently been updated again.  It mostly still works,
   but some of the features are now broken.

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

