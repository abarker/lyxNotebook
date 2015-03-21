# -*- coding: utf-8 -*-
"""

This file only contains the keymap for Lyx Notebook.  The keys can be
arbitrarily set by changing them from this file (though, of course, collisions
with other key mappings and convenience should be considered).

Any key which is bound to a Lyx Notebook function should also be bound to the
Lyx LFUN "server-notify" in the Lyx .bind file (which the install program creates
as lyxNotebookKeyBindings.bind in the user's Lyx home directory)!

To modify a key mapping in this file, simply change the string (or the None value)
in the first component of a 2-tuple in the list "allCommandsAndKeymap" below.
The associated command strings in the second component of the 2-tuples should
not be changed at all, or bugs will occur.

The string names which are used for the keys must be the same as the string
names which are reported by the Lyx server-notify LFUN.  To find the name for a
key, press it in Lyx while looking at the status-bar on the lower left.  The
name of the key will briefly appear (except in some cases when it is already
bound to something).  That is the string which should be used.  In particular,
the prefixes "Shift+", "Alt+", and "Control+" are used instead of the shorter
forms "S-", "M-", and "C-" which are used in the Lyx .bind file.

To avoid collisions with the "usual" mappings, see, e.g.,
   http://en.wikipedia.org/wiki/Table_of_keyboard_shortcuts
for which keys are used by the OS.  Beware alt-F4 in KDE, close window.  The
default LyX bindings can be found in whatever .bind file is being used, such
as cua.bind in the Lyx system (try "locate cua.bind" on the command line).

Note that the F9 and F10 keys are unavailable in KDE: they are the window walk
forward/backward keys.

"""

allCommandsAndKeymap = [
    ("F1", "pop up submenu"),
    # Goto cell commands.
    (None, "goto next any cell"),
    (None, "goto prev any cell"),
    (None, "goto next code cell"),
    (None, "goto prev code cell"),
    ("F2", "goto next init cell"),
    ("Shift+F2", "goto prev init cell"),
    ("F3", "goto next standard cell"),
    ("Shift+F3", "goto prev standard cell"),

    # Ordinary cell-evaluate commands, done explicitly in Lyx.
    ("F4", "evaluate current cell"),
    (None, "evaluate current cell after reinit"),
    ("F5", "evaluate all code cells"),
    ("Shift+F5", "evaluate all code cells after reinit"),
    ("F6", "evaluate all init cells"),
    ("Shift+F6", "evaluate all init cells after reinit"),
    ("F7", "evaluate all standard cells"),
    ("Shift+F7", "evaluate all standard cells after reinit"),

    # Batch cell-evaluation commands.
    (None, "toggle buffer replace on batch eval"),
    (None, "revert to most recent batch eval backup"),
    (None, "batch evaluate all code cells"),
    (None, "batch evaluate all code cells after reinit"),
    (None, "batch evaluate all init cells"),
    (None, "batch evaluate all init cells after reinit"),
    (None, "batch evaluate all standard cells"),
    (None, "batch evaluate all standard cells after reinit"),

    # Misc commands.
    ("F8", "reinitialize current interpreter"),
    ("Shift+F8", "reinitialize all interpreters for buffer"),
    (None, "reinitialize all interpreters for all buffers"),
    (None, "write all code cells to files"),
    # Note F9 and F10 are unavailable in KDE: window walk forward/backward.
    # Shift+F10 is currently free
    ("Shift+F9", "insert most recent graphic file"),
    ("Shift+F12", "kill lyx notebook process"),
    (None, "prompt echo on"),
    (None, "prompt echo off"),
    ("Shift+F1", "toggle prompt echo"),
    ("Shift+F4", "evaluate newlines as current cell"),

    # Open and close cell commands.
    ("F11", "open all cells"),
    ("Shift+F11", "close all cells"),
    (None, "open all output cells"),
    (None, "close all output cells")
]

