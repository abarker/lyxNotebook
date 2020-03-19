# -*- coding: utf-8 -*-
"""

=========================================================================
This file is part of LyX Notebook, which works with LyX but is an
independent project.  License details (MIT) can be found in the file
COPYING.

Copyright (c) 2012 Allen Barker
=========================================================================

Simple GUI elements used by the program.

"""

import pathlib
import PySimpleGUI as sg

sg.theme("SystemDefault")

popup_location = 100, 100 # Display is nicer with fixed popup location.

def yesno_popup(message, title):
    """A simple blocking popup asking for confirmation."""
    yesno = sg.popup_yes_no(message,
                            title=title,
                            button_color=None,
                            background_color=None,
                            text_color=None,
                            line_width=None,
                            font=None,
                            no_titlebar=False,
                            grab_anywhere=False,
                            keep_on_top=True,
                            location=popup_location)
    return yesno == "Yes"

def text_info_popup(text, title):
    """A simple blocking popup displaying text for the user to read and confirm."""
    sg.popup(text,
        title=title,
        button_color=None,
        background_color=None,
        text_color=None,
        button_type=0,
        custom_text=(None, None),
        non_blocking=False,
        icon=None,
        line_width=None,
        font=None,
        no_titlebar=False,
        grab_anywhere=False,
        keep_on_top=False,
        location=popup_location)

def get_path_popup(message, title, default_path, *, directory=False):
    """Query to get a pathname.  If `directory` is true then it browses for directories
    instead of files."""
    if not directory:
        path = sg.popup_get_file(message,
                                 title=title,
                                 default_path=default_path,
                                 default_extension="",
                                 save_as=False,
                                 multiple_files=False,
                                 file_types=(('ALL Files', '*.*'),),
                                 no_window=False,
                                 size=(None, None),
                                 button_color=None,
                                 background_color=None,
                                 text_color=None,
                                 icon=None,
                                 font=None,
                                 no_titlebar=False,
                                 grab_anywhere=False,
                                 keep_on_top=True,
                                 location=popup_location,
                                 initial_folder=pathlib.Path.home())
    else:
        path = sg.popup_get_folder(message,
                                 title=title,
                                 default_path=default_path,
                                 no_window=False,
                                 size=(None, None),
                                 button_color=None,
                                 background_color=None,
                                 text_color=None,
                                 icon=None,
                                 font=None,
                                 no_titlebar=False,
                                 grab_anywhere=False,
                                 keep_on_top=True,
                                 location=popup_location,
                                 initial_folder=pathlib.Path.home())
    return path

