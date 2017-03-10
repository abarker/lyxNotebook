#! /usr/bin/python
# -*- coding: utf-8 -*-
"""

=========================================================================
This file is part of LyX Notebook, which works with LyX but is an
independent project.  License details (MIT) can be found in the file
COPYING.

Copyright (c) 2012 Allen Barker
=========================================================================

This program automates the install and setup process.

The user's home Lyx directory is read from `lyxNotebook_user_settings.py` (the
directory is assumed by default to be `~/.lyx`, but that file can be modified).

The bind files `userCustomizableKeyBindings.bind` and `lyxNotebookKeyBindings.bind`
are generated from the corresponding `.template` files.
The resulting `.bind` files are copied to the user's home Lyx directory.
The `install.py` program will ask before overwriting either of these files.

The main bind file is `userCustomizableKeyBindings.bind`, which should be set
as the active LyX bind file.  A `\\bind_file` command in that file then loads
`lyxNotebookKeyBindings.bind`.  That line can be commented-out whenever the
user does not want the function key bindings overwritten.  Similarly, the user
can load-in his or her own personal `.bind` file, or just add personal bindings
directly in the file itself.

The `.module` files are always copied to the layouts directory in the user's
home Lyx directory.  The names of the module files are assumed to be unique
enough to avoid any conflicts with existing files.  (Old files may need to be
removed by hand, however, if the `.module` files are regenerated after changes
are made to the insetSpecifier interpreterSpec for an interpreter.)

"""

from __future__ import print_function, division
import sys
import os
import shutil
import glob
from os import path
# import easygui
import easygui_096 as easygui # Use a locally modified version of easygui.
import lyxNotebook_user_settings

userHomeLyxDirectory = lyxNotebook_user_settings.userHomeLyxDirectory
userHomeLyxDirectoryExpanded = path.expanduser(userHomeLyxDirectory)

print("="*70)
print("\nStarting the install and setup of LyX Notebook...\n")

# Find the Lyx Notebook source directory from the invoking pathname and cwd.
invokingCommand = path.expanduser(sys.argv[0])
cwd = os.getcwd()
absPathToSetupProg = path.join(cwd, invokingCommand) # TODO see utilities.py

sourceDir = path.dirname(path.normpath(absPathToSetupProg))
print("The absolute path of the Lyx Notebook source directory is:\n   ", sourceDir)

sourceDirWithTilde = path.join("~", path.relpath(sourceDir, path.expanduser("~")))
print("\nThe path of the Lyx Notebook source directory relative to home is:\n   ",
      sourceDirWithTilde, "\n")

#
# User-modifiable key-binding file (TODO: better as a fun or 3).
#

# Process the user-modifiable bind file to load the path of the Lyx Notebook bindings.
bindTemplatePathname = path.join(
    sourceDir, "filesForDotLyxDir", "userCustomizableKeyBindings.template")
bindTemplate = open(bindTemplatePathname, "r")
bindContentsStr = bindTemplate.read()
bindTemplate.close()
bindContentsStr = bindContentsStr.replace("<<userHomeLyxDirectory>>",
                         lyxNotebook_user_settings.userHomeLyxDirectory) # not expanded

# Write out the final user-modifiable .bind file.
bindFilePathname = path.join(
    sourceDir, "filesForDotLyxDir", "userCustomizableKeyBindings.bind")
bindFile = open(bindFilePathname, "w")
bindFile.write(bindContentsStr)
bindFile.close()
print("Generated the key-binding file\n   ",
      bindFilePathname, "\nfrom the corresponding .template file.")

# Copy the user-modifiable .bind file to the userHomeLyxDirectory.
bindFileDest = path.join(
    userHomeLyxDirectoryExpanded, "userCustomizableKeyBindings.bind")
yesno = 1
if os.path.exists(bindFileDest):
    msg = "File\n   " + bindFileDest + "\nalready exists.  Overwrite?"
    yesno = easygui.ynbox(msg, "LyX Notebook Setup")
if yesno == 1:
    shutil.copyfile(bindFilePathname, bindFileDest)
    print("\nCopied the generated key-binding file to the home LyX directory:\n   ",
          bindFileDest, "\n")
else:
    print("\nDid not overwrite existing key-binding in the LyX home directory:\n   ",
          bindFileDest, "\n")
os.remove(bindFilePathname) # delete local copy to avoid confusion

#
# Lyx Notebook key-binding file (TODO better as a fun call or three, repeated code)
# Note that the LFUN to run prog *requires* a full pathname, not a relative one.
#

# Process the Lyx Notebook bind file to contain the path of the user's source directory.
bindTemplatePathname = path.join(
    sourceDir, "filesForDotLyxDir", "lyxNotebookKeyBindings.template")
bindTemplate = open(bindTemplatePathname, "r")
bindContentsStr = bindTemplate.read()
bindTemplate.close()
bindContentsStr = bindContentsStr.replace("<<absPathToLyxNotebookSourceDir>>",
                                          sourceDir) # must be absolute path

# Write out the final Lyx Notebook .bind file.
bindFilePathname = path.join(
    sourceDir, "filesForDotLyxDir", "lyxNotebookKeyBindings.bind")
bindFile = open(bindFilePathname, "w")
bindFile.write(bindContentsStr)
bindFile.close()
print("Generated the key-binding file\n   ",
      bindFilePathname, "\nfrom the corresponding .template file.")

# Copy the Lyx Notebook .bind file to the userHomeLyxDirectory.
bindFileDest = path.join(
    userHomeLyxDirectoryExpanded, "lyxNotebookKeyBindings.bind")
yesno = 1
if os.path.exists(bindFileDest):
    msg = "File\n   " + bindFileDest + "\nalready exists.  Overwrite?"
    yesno = easygui.ynbox(msg, "LyX Notebook Setup")
if yesno == 1:
    shutil.copyfile(bindFilePathname, bindFileDest)
    print("\nCopied the generated key-binding file to the home LyX directory:\n   ",
          bindFileDest, "\n")
else:
    print("\nDid not overwrite existing key-binding in the LyX home directory:\n   ",
          bindFileDest, "\n")
os.remove(bindFilePathname) # delete local copy to avoid confusion

#
# The .module files
#

# Go to the directory for .module files.
modulesDirectory = path.join(sourceDir, "filesForDotLyxLayoutsDir")
os.chdir(modulesDirectory)

# First remove any old .module files in that directory.
print("Regenerating all the .module files:")
dotModuleFiles = glob.glob("*.module")
for oldModuleFile in dotModuleFiles: # delete the old .module files
    os.remove(oldModuleFile)
    installed = os.path.join(userHomeLyxDirectoryExpanded, "layouts", oldModuleFile)
    if os.path.exists(installed): os.remove(installed)

# Regenerate all the .module files, in case the user changed interpreter_specs.py.
#os.system("python generateModuleFilesFromTemplate.py")
# TODO Below is a temporary refactoring step to clean up the whole setup and
# not use os.system.
sys.path.insert(0, ".") # We did a chdir above to the dir.
from generateModuleFilesFromTemplate import generate_files_from_templates
generate_files_from_templates()
del sys.path[0]

# Copy all the .module files to the layouts directory.
print("\nCopying the regenerated .module files to the LyX layouts directory.")
dotModuleFiles = glob.glob("*.module")
for newModuleFile in dotModuleFiles:
    pathInLayoutsDir = path.join(
        userHomeLyxDirectoryExpanded, "layouts", newModuleFile)
    shutil.copyfile(newModuleFile, pathInLayoutsDir)

msg = "Finished the first phase of the setup."
text = """Finished the first phase of the LyX Notebook setup.  Next do the following
steps to finish the setup.  (You can keep this window open as a reminder.)

   1) Open LyX.

   2) Goto the menu
           Tools > Preferences > Editing > Shortcuts
      and enter the filename
           ~/.lyx/userCustomizableKeyBindings
      in the "Bind file" box on the top right; enter it WITHOUT any .bind suffix.
      (Modify the above in the obvious way if ~/.lyx is not your home Lyx directory;
      in this case you'll also need to modify a line in lyxNotebook_user_settings.py.)

   3) While still in the preferences menu, check
           Tools > Preferences > Paths
      and make sure that the "LyXServer pipe" setting is ~/.lyx/lyxpipe (replacing
      ~/.lyx with your home Lyx directory if it is different).  You can use some
      other setting, but in that case you'll also need to modify a line in
      lyxNotebook_user_settings.py.

   3) Select the menu item
           Tools > Reconfigure

   4) Close LyX and then reopen it.

LyX Notebook should now be usable.  For each document you still need to go to
     Document > Settings > Modules
and add the module for each cell-language which you wish to use in the
document.  The cells themselves can then be found on the menu:
     Insert > Custom Insets

Press F12 in LyX to start the LyX Notebook program (Shift+F12 to kill it)
Press F1 for a menu of all the commands and their current key bindings.
See the documentation file lyxNotebookDocs.pdf for further information.

"""

print("="*70)
print("\n" + text)
easygui.textbox(msg=msg, text=text, title="LyX Notebook Setup")

