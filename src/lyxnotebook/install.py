"""

=========================================================================
This file is part of LyX Notebook, which works with LyX but is an
independent project.  License details (MIT) can be found in the file
COPYING.

Copyright (c) 2012 Allen Barker
=========================================================================

This program automates the install and setup process.

The user's home Lyx directory is read from `lyxnotebook.cfg` (the
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
are made to the inset_specifier interpreter_spec for an interpreter.)

"""

import sys
import os
import shutil
import glob
from os import path
import platform
import tempfile
import PySimpleGUI as sg
from .config_file_processing import config_dict
from .interpreter_specs.generate_module_files_from_template import generate_module_files_from_templates
from .gui import get_path_popup, yesno_popup, text_info_popup

python_version = platform.python_version_tuple()

def find_source_directory():
    """Find the Lyx Notebook source directory from the invoking pathname and cwd."""
    abs_path_to_setup_prog = os.path.abspath(__file__)

    source_dir = path.dirname(abs_path_to_setup_prog)
    print("The absolute path of the Lyx Notebook source directory is:\n   ", source_dir)

    source_dir_with_tilde = path.join("~", path.relpath(source_dir, path.expanduser("~")))
    print("\nThe path of the Lyx Notebook source directory relative to home is:\n   ",
          source_dir_with_tilde, "\n")
    return source_dir

def setup_key_binding_files(lyx_user_directory, source_dir,
                            lyxNotebook_run_script_path):
    """Set up the user-modifiable key-binding file.  The `lyxNotebook_run_script_path`
    path to the script that runs LyxNotebook must be an absolute path."""
    if not os.path.isdir(lyx_user_directory):
        print("No .lyx directory found at specified location.  Run LyX first to create it.")
        sys.exit(1)

    # Process the user-modifiable bind file to load the path of the Lyx Notebook bindings.
    bind_template_pathname = path.join(
        source_dir, "templates_for_bind_files", "userCustomizableKeyBindings.template")
    with open(bind_template_pathname, "r") as bind_template:
        bind_contents_str = bind_template.read()
    bind_contents_str = bind_contents_str.replace("<<lyx_user_directory>>",
                                                  lyx_user_directory)

    with tempfile.TemporaryDirectory() as tmpdir_name:
        # Write out the final user-modifiable .bind file to the temp dir.
        bind_file_pathname = path.join(tmpdir_name, "userCustomizableKeyBindings.bind")
        with open(bind_file_pathname, "w") as bind_file:
            bind_file.write(bind_contents_str)
        print("Generated the key-binding file\n   ", bind_file_pathname,
                "\nfrom the corresponding .template file.")

        # Copy the user-modifiable .bind file to lyx_user_directory.
        bind_file_dest = path.join(lyx_user_directory,
                                   "userCustomizableKeyBindings.bind")
        yesno = True
        if os.path.exists(bind_file_dest):
            msg = "File\n   " + bind_file_dest + "\nalready exists.  Overwrite?"
            yesno = yesno_popup(msg, "LyX Notebook Setup")
        if yesno:
            shutil.copyfile(bind_file_pathname, bind_file_dest)
            print("\nCopied the generated key-binding file to the home LyX directory:\n   ",
                  bind_file_dest, "\n")
        else:
            print("\nDid not overwrite existing key-binding in the LyX home directory:\n   ",
                  bind_file_dest, "\n")

    #
    # Lyx Notebook key-binding file (TODO better as a fun call or three, repeated code)
    # Note that the LFUN to run prog *requires* a full pathname, not a relative one.
    #

    # Process the Lyx Notebook bind file to contain the path of the user's source directory.
    bind_template_pathname = path.join(
        source_dir, "templates_for_bind_files", "lyxNotebookKeyBindings.template")
    with open(bind_template_pathname, "r") as bind_template:
        bind_contents_str = bind_template.read()
    bind_contents_str = bind_contents_str.replace("<<lyxNotebook_run_script_path>>",
                                              lyxNotebook_run_script_path) # MUST be absolute path!

    with tempfile.TemporaryDirectory() as tmpdir_name:
        # Write out the final Lyx Notebook .bind file to the temporary directory.
        bind_file_pathname = path.join(tmpdir_name, "lyxNotebookKeyBindings.bind")
        with open(bind_file_pathname, "w") as bind_file:
            bind_file.write(bind_contents_str)
        print("Generated the key-binding file\n   ",
              bind_file_pathname, "\nfrom the corresponding .template file.")

        # Copy the Lyx Notebook .bind file to lyx_user_directory.
        bind_file_dest = path.join(
            lyx_user_directory, "lyxNotebookKeyBindings.bind")
        yesno = True
        if os.path.exists(bind_file_dest):
            msg = "File\n   " + bind_file_dest + "\nalready exists.  Overwrite?"
            yesno = yesno_popup(msg, "LyX Notebook Setup")
        if yesno:
            shutil.copyfile(bind_file_pathname, bind_file_dest)
            print("\nCopied the generated key-binding file to the home LyX directory:\n   ",
                  bind_file_dest, "\n")
        else:
            print("\nDid not overwrite existing key-binding in the LyX home directory:\n   ",
                  bind_file_dest, "\n")

def setup_module_files(lyx_user_directory, source_dir, has_editable_insets):
    """Generate the .module files and copy to `lyx_user_directory`"""
    # Go to the directory for .module files.
    #tmp_modules_dir = path.join(source_dir, "files_for_dot_lyx_layouts_dir")
    prev_dir = os.curdir
    with tempfile.TemporaryDirectory() as tmp_modules_dir:
        os.chdir(tmp_modules_dir)

        ## First remove any old .module files in that directory.
        #print("Regenerating all the .module files:")
        #dot_module_files = glob.glob("*.module")
        #for oldModuleFile in dot_module_files: # Delete the old .module files.
        #    os.remove(oldModuleFile)
        #    installed = os.path.join(lyx_user_directory, "layouts", oldModuleFile)
        #    if os.path.exists(installed):
        #        os.remove(installed)

        # Regenerate all the .module files, in case the user changed interpreter specs.
        generate_module_files_from_templates(tmp_modules_dir, has_editable_insets)

        # Copy all the .module files to the layouts directory.
        print("\nCopying the regenerated .module files to the LyX layouts directory.")
        dot_module_files = glob.glob("*.module")
        for new_module_file in dot_module_files:
            path_in_layouts_dir = path.join(lyx_user_directory,
                                            "layouts", new_module_file)
            shutil.copyfile(new_module_file, path_in_layouts_dir)

    os.chdir(prev_dir)

def setup_config_file(lyx_user_dir, source_dir, has_editable_insets):
    """Copy the default config file to the `lyx_user_dir`."""
    config_file_path = os.path.join(lyx_user_dir, "lyxnotebook.cfg")
    default_config_file_path = os.path.join(source_dir,
            "default_config_file_and_data_files", "default_config_file.cfg")
    with open(default_config_file_path, "r") as f:
        default_config_file_str = f.read()

    if not has_editable_insets:
        print("\nSetting up config file with `has_editable_insets` false.""")
        edit_line = "\nhas_editable_insets = true"
        replace_line = "\nhas_editable_insets = false"
        default_config_file_str = default_config_file_str.replace(edit_line, replace_line)

    yesno = True
    if os.path.exists(config_file_path):
        msg = "File\n   " + config_file_path + "\nalready exists.  Overwrite?"
        yesno = yesno_popup(msg, "LyX Notebook Setup")
    if yesno:
        with open(config_file_path, "w") as f:
            f.write(default_config_file_str)
        print("\nCopied the default config file to the LyX user directory:\n   ",
              config_file_path, "\n")
    else:
        print("\nDid not overwrite existing config file in the LyX user directory:\n   ",
              config_file_path, "\n")

def run_setup(lyx_user_dir, lyxNotebook_run_script_path, has_editable_insets):
    """Main routine to run the setup.  Pass in the full path to the startup script
    (which calls this routine) so it can be set to be called from a function key in
    Lyx."""
    print()
    print("="*70)
    print("\nStarting the install and setup of LyX Notebook...\n")

    # Find the Lyx Notebook source directory from the invoking pathname and cwd.
    source_dir = find_source_directory()
    os.chdir(source_dir) # So the relevant data directories can be located.

    setup_config_file(lyx_user_dir, source_dir, has_editable_insets)

    setup_key_binding_files(lyx_user_dir, source_dir,
                            lyxNotebook_run_script_path)

    setup_module_files(lyx_user_dir, source_dir, has_editable_insets)

    # Finished the first phase.
    text = """Finished the first phase of the LyX Notebook setup.  Next do the following
    steps to finish the setup.  (You can keep this window open as a reminder.)

       1) Open LyX.

       2) Goto the menu
               Tools > Preferences > Editing > Shortcuts
          and enter the filename
               ~/.lyx/userCustomizableKeyBindings
          in the "Bind file" box on the top right; enter it WITHOUT any .bind suffix.
          (Modify the above in the obvious way if ~/.lyx is not your home Lyx directory;
          in this case you'll also need to modify a line in the lyxnotebook.cfg file.)

       3) While still in the preferences menu, check
               Tools > Preferences > Paths
          and make sure that the "LyXServer pipe" setting is ~/.lyx/lyxpipe (replacing
          ~/.lyx with your home Lyx directory if it is different).  You can use some
          other setting, but in that case you'll also need to modify a line in
          the lyxnotebook.cfg file.

       3) Select the menu item
               Tools > Reconfigure

       4) Close LyX and then reopen it.

    LyX Notebook should now be usable.  For each document you still need to go to
         Document > Settings > Modules
    and add the module for each cell-language which you wish to use in the
    document.  The cells themselves can then be found on the menu:
         Insert > Custom Insets

    Press F12 in LyX to start the LyX Notebook program (Shift+F12 to kill it).
    Press F1 for a menu of all the commands and their current key bindings.
    See the documentation file lyxNotebookDocs.pdf for further information.

    """
    print("="*70)
    print("\n" + text)
    text_info_popup(text, title="LyX Notebook Setup")

