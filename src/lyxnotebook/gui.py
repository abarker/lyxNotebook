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
from .config_file_processing import config_dict

# For persistent GUI inside an event loop, note that the current main event loop
# for getting and executing commands is in the method `server_notify_loop` of
# the main `ControllerOfLyxAndInterpreters` instance.

sg.theme("DefaultNoMoreNagging")

popup_location = 100, 100 # Display is nicer with fixed popup location.

default_title = "LyX Notebook"

def yesno_popup(message, title=default_title):
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

def text_info_popup(text, title=default_title):
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

def text_warning_popup(text, title=default_title):
    """A simple blocking popup displaying warning text for the user to read and confirm.
    As of not it is the same as `text_info_popup` except it is always on top."""
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
        keep_on_top=True,
        location=popup_location)

def get_path_popup(message, default_path, *, title=default_title, directory=False):
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

def main_lyxnotebook_gui_window(menu_items_list, title=default_title):
    """Pop up a menu with a list of choices."""
    height = len(menu_items_list)
    width = max(len(line) for line in menu_items_list)

    listbox = sg.Listbox(values=menu_items_list,
                         default_values=None,
                         select_mode=None,
                         change_submits=False,
                         enable_events=False, # Don't return user's click immediately.
                         bind_return_key=False,
                         size=(width, height),
                         disabled=False,
                         auto_size_text=None,
                         font="TkFixedFont", # Tkinter monospace.
                         no_scrollbar=False,
                         background_color=None,
                         text_color=None,
                         key="cmd list",
                         pad=None,
                         tooltip=None,
                         right_click_menu=None,
                         visible=True,
                         metadata=None)

    layout = [ [listbox], [sg.Cancel()] ]

    window = sg.Window(title=title,
                       layout=layout,
                       default_element_size=(45, 1),
                       default_button_element_size=(None, None),
                       auto_size_text=None,
                       auto_size_buttons=None,
                       location=popup_location,
                       size=(None, None),
                       element_padding=None,
                       margins=(None, None),
                       button_color=None,
                       font=None,
                       progress_bar_color=(None, None),
                       background_color=None,
                       border_depth=None,
                       icon=None,
                       force_toplevel=False,
                       alpha_channel=1,
                       return_keyboard_events=False,
                       use_default_focus=True,
                       text_justification=None,
                       no_titlebar=False,
                       grab_anywhere=False,
                       keep_on_top=config_dict["gui_window_always_on_top"],
                       resizable=False,
                       disable_close=False,
                       disable_minimize=False,
                       right_click_menu=None,
                       transparent_color=None,
                       debugger_enabled=True,
                       finalize=False,
                       element_justification="left",
                       ttk_theme=None,
                       use_ttk_buttons=None,
                       metadata=None)

    # A read is needed before an update, according to manual.
    btn, values_dict = window.Read(timeout=0)
    return window

def read_menu_event(window, choices, timeout=None):
    """Reads the window event.  Return `None` if no event to respond to, otherwise
    return the selected menu item's text."""
    event, values = window.read(timeout=timeout)

    if not event:
        return "toggle gui"

    # Update the values to clear the current selection, since we've read it.
    window["cmd list"].update(values=choices)

    if event == "Cancel":
        return "toggle gui"

    if not values or not values["cmd list"]:
        return None # Got no command, do nothing.

    return values["cmd list"][0]

def close_menu(window):
    """Close the window `window`."""
    window.close()

