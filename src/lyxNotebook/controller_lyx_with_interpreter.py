# -*- coding: utf-8 -*-
"""

=========================================================================
This file is part of LyX Notebook, which works with LyX but is an
independent project.  License details (MIT) can be found in the file
COPYING.

Copyright (c) 2012 Allen Barker
=========================================================================

This is the main module of the Lyx Notebook program; the `lyxNotebook.py` script
just does basic startup stuff like making sure a Lyx Notebook process is not
already running.

This module contains the implementation of the high-level controller class
`ControllerLyxWithInterpreter`.  This class mediates between the Lyx program
and one or more interpreters for interpreting code.  It gets basic commands
from Lyx, executes them, and pushes the appropriate actions back to Lyx.  Some
of these actions involve running code in an interpreter.  In these cases, the
controller sends the code to the appropriate interpreter, gets the results
back, and then pushes the results to Lyx.

"""

from __future__ import print_function, division
#import easygui as eg
import easygui_096 as eg # Use a local, modified version.
import re
import sys
import os
import time
import signal

# Local file imports.
import lyxNotebook_user_settings
from interact_with_lyx_cells import InteractWithLyxCells, Cell
from external_interpreter import ExternalInterpreter
import interpreter_specs # Specs for all the interpreters which are allowed.
import keymap # The current mapping of keys to Lyx Notebook functions.


class IndentCalc(object):
    """A class that is used for Python cells, to calculate the indentation
    levels.  This is used so that users can write code like in a file, without
    the extra blank lines which are often required in the interpreter.  A blank
    line is sent automatically when the code indentation level reaches zero,
    going downward.

    The class must calculate explicit and implicit line continuations, since this
    affects the indentation calculation.   The indentation is also incremented
    if a colon is found on a line but not in a comment, string, or within any
    parens, curly braces, or brackets.  This is to handle one-liners like
       "if x==4: return"
    After handling colons the calculated indententation values are no longer
    strictly correct literally, but they still works in the "down to zero"
    calculation, which is what is important.

    An instance of this object should be passed each physical line, one by one.
    It then makes calculations concerning the logical line structure.  There
    are no side effects, so results can be ignored for non-Python code."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.parens = 0
        self.brackets = 0
        self.curlys = 0
        self.in_string1 = False
        self.in_string2 = False
        self.backslash_continuation = False
        self.indentation_level = 0
        self.indentation_level_down_to_zero = False

    def in_string_literal(self):
        return self.in_string1 or self.in_string2

    def in_paren_bracket_curly(self):
        return self.parens > 0 or self.brackets > 0 or self.curlys > 0

    def in_explicit_line_continuation(self):
        return self.backslash_continuation

    def in_implicit_line_continuation(self):
        return self.in_paren_bracket_curly() or self.in_string2

    def in_line_continuation(self):
        return self.in_explicit_line_continuation() or self.in_implicit_line_continuation()

    def indent_level(self):
        return self.indentation_level

    def indent_level_down_to_zero(self):
        return self.indentation_level_down_to_zero

    def update_for_physical_line(self, code_line):
        """The IndentCalc class should be sequentially passed physical lines, via
        this function."""

        # "indentation down to zero" is only considered true right after the first
        # non-continued physical line which has indentation level zero when the
        # previous line had a higher level, so always reset for each physical line
        self.indentation_level_down_to_zero = False

        # detect a blank line (possibly with a comment) and do nothing else
        stripped_line = code_line.rstrip() # strip off trailing whitespace
        if len(stripped_line) == 0:
            self.backslash_continuation = False # assume blanks unset explicit continuation
            return
        first_nonwhitespace = re.search("\S", stripped_line)
        if first_nonwhitespace == "#":
            self.backslash_continuation = False
            return

        # update the indentation level (unless line is continued)
        if not self.in_line_continuation():
            new_level = first_nonwhitespace.start()
            if self.indentation_level > 0 and new_level == 0:
                self.indentation_level_down_to_zero = True
            self.indentation_level = new_level

        # backslash continuation only holds for one line (unless reset later at end)
        # this was already used in calculating self.in_line_continuation() above
        self.backslash_continuation = False

        # go through each char in the line, updating paren counts, etc.
        # note that i is the index into the line stripped_line
        backslash_escape = False
        # fake a C-style loop, so we can jump ahead easily by resetting i
        i = -1
        while True:

            i += 1
            if i >= len(stripped_line): break
            char = stripped_line[i]

            # first handle backslash escape mode... we always ignore the next char,
            # and the only cases we care about are one-character backslash escapes
            # (let Python worry about any syntax errors with backslash outside strings)
            if backslash_escape:
                backslash_escape = False
                continue

            # handle the backslash char, either line continuation or escape
            if char == "\\":
                if i == len(stripped_line) - 1: # line continuation
                    self.backslash_continuation = True
                    continue # could also break, since at end of line
                else: # start a backslash escape
                    # this is only valid in strings, but let Python catch any errors there
                    backslash_escape = True
                    continue

            # look for string delimiters and toggle string modes
            if char == "\"":
                # if in a string, then we got the closing quote
                if self.in_string1: self.in_string1 = False
                # check if this is part of a triple-quote string
                elif (i <= len(stripped_line) - 3 and
                      stripped_line[i+1] == "\"" and stripped_line[i+2] == "\""):
                    if self.in_string2: self.in_string2 = False
                    else: self.in_string2 = True
                    i += 2 # increment past the second two quotes of the triple-quote
                # otherwise we start a new single-quote string
                else: self.in_string1 = True
                continue

            # ignore all else inside strings
            if self.in_string_literal(): continue

            # if at a comment begin then nothing more to do
            if char == "#": break

            # update counts for general delimiters
            if char == "(": self.parens += 1
            elif char == ")": self.parens -= 1
            elif char == "[": self.brackets += 1
            elif char == "]": self.brackets -= 1
            elif char == "{": self.curlys += 1
            elif char == "}": self.curlys -= 1

            # Increase indent if a colon is found not inside a comment, string,
            # or any paren/bracket/curly delimiters.  We've already ruled out all
            # cases but those delimeters above.
            #
            # This is to allow one-liners like
            #   def sqr(x): return x*x
            # and like the "if" line below.
            #
            # The indent level will not be exact when separate-line colons are found,
            # but the "down to zero" will work.  This could be improved, if necessary,
            # by checking whether the colon is at the end of the line (except for
            # whitespace and comments) and not incrementing in those cases.
            if char == ":" and not self.in_paren_bracket_curly(): self.indentation_level += 3
        return


class InterpreterProcess(object):
    """An instance of this class represents a data record for a running
    interpreter process.  Contains an ExternalInterpreter instance for that
    process, but also has an IndentCalc instance, and keeps track of the most
    recent prompt received from the interpreter."""

    def __init__(self, spec):
        self.spec = spec
        self.most_recent_prompt = self.spec["main_prompt"]
        self.indent_calc = IndentCalc()
        self.external_interp = ExternalInterpreter(self.spec)


class InterpreterProcessCollection(object):
    """A class to hold multiple InterpreterProcess instances.  There will
    probably only be a single instance, but multiple instances should not cause
    problems.  Basically a dict mapping (bufferName,inset_specifier) tuples to
    InterpreterProcess class instances.  Starts processes when necessary."""

    def __init__(self, current_buffer):
        if lyxNotebook_user_settings.separate_interpreters_for_each_buffer is False:
            current_buffer = "___dummy___" # force all to use same buffer if not set
        self.interpreter_spec_list = [specName.params
                                    for specName in interpreter_specs.all_specs]
        self.num_specs = len(self.interpreter_spec_list)
        self.inset_specifier_to_interpreter_spec_dict = {}
        self.all_inset_specifiers = []
        for spec in self.interpreter_spec_list:
            self.inset_specifier_to_interpreter_spec_dict[spec["inset_specifier"]] = spec
            self.all_inset_specifiers.append(spec["inset_specifier"])
        self.reset_all_interpreters_for_all_buffers(current_buffer)

    def reset_all_interpreters_for_all_buffers(self, current_buffer=""):
        """Reset all the interpreters, restarting any not-on-demand ones for the
        buffer current_buffer (unless it equals the empty string).  This also
        frees any processes for former buffers, such as for closed buffers and
        renamed buffers."""
        self.main_dict = {} # map (bufferName,inset_specifier) tuple to InterpreterProcess
        # Start up not-on-demand interpreters, but only for the current buffer
        # (in principle we could use buffer-next to get all buffers and start for all,
        # but they may not all even # use Lyx Notebook).
        if current_buffer != "":
            self.reset_for_buffer(current_buffer)

    def reset_for_buffer(self, buffer_name, inset_specifier=""):
        """Reset the interpreter for inset_specifier cells for buffer buffer_name.
        Restarts the whole process.  If inset_specifier is the empty string then
        reset for all inset specifiers."""
        if lyxNotebook_user_settings.separate_interpreters_for_each_buffer is False:
            buffer_name = "___dummy___" # force all to use same buffer if not set
        inset_specifier_list = [inset_specifier]
        if inset_specifier == "": # do all if empty string
            inset_specifier_list = self.all_inset_specifiers
        for inset_specifier in inset_specifier_list:
            key = (buffer_name, inset_specifier)
            spec = self.inset_specifier_to_interpreter_spec_dict[inset_specifier]
            if key in self.main_dict: del self.main_dict[key]
            if not spec["run_only_on_demand"]:
                self.get_interpreter_process(buffer_name, inset_specifier)

    def get_interpreter_process(self, buffer_name, inset_specifier):
        """Get interpreter process, creating/starting one if one not there already."""
        if lyxNotebook_user_settings.separate_interpreters_for_each_buffer is False:
            buffer_name = "___dummy___" # force all to use same buffer if not set
        key = (buffer_name, inset_specifier)
        if not key in self.main_dict:
            msg = "Starting interpreter for " + inset_specifier
            if lyxNotebook_user_settings.separate_interpreters_for_each_buffer is True:
                msg += ", for buffer:\n   " + buffer_name
            print(msg)
            self.main_dict[key] = InterpreterProcess(
                self.inset_specifier_to_interpreter_spec_dict[inset_specifier])
        return self.main_dict[key]

    def print_start_message(self):
        start_msg = "Running for " + str(self.num_specs) + \
            " possible interpreters (cell languages):\n"
        interp_str = ""
        for i in range(self.num_specs):
            interp_str += "      " + self.interpreter_spec_list[i]["inset_specifier"]
            interp_str += " (label=\"" + self.interpreter_spec_list[i]["prog_name"] + "\""
            if not self.interpreter_spec_list[i]["run_only_on_demand"]:
                interp_str += ", autostarted in current buffer"
            interp_str += ")\n"
        start_msg += interp_str
        print(start_msg)


class ControllerLyxWithInterpreter(object):
    """This class is the high-level controller class which deals with user
    interactions and which manages the Lyx process and the interpreter processes.
    The interpreter specifications are read from the module interpreter_specs.  The
    list interpreter_specs.all_specs in that module is assumed to contains all the
    specs."""

    def __init__(self, clientname):

        self.no_echo = lyxNotebook_user_settings.no_echo
        self.buffer_replace_on_batch_eval = lyxNotebook_user_settings.buffer_replace_on_batch_eval

        # Set up interactions with Lyx.
        self.clientname = clientname
        self.lyx_process = InteractWithLyxCells(clientname)

        # Initialize the collection of interpreter processes.
        self.all_interps = InterpreterProcessCollection(
            self.lyx_process.server_get_filename()) # buffer name is file name
        self.all_interps.print_start_message()

        # Display a startup notification message in Lyx.
        message = "LyX Notebook is now running..."
        self.lyx_process.show_message(message)
        #self.display_popup_message(message=message, text=startMsg, seconds=3)

        # Start up the command loop.
        self.server_notify_loop()
        return # never executed; command loop above continues until sys.exit

    def reset_interpreters_for_buffer(self, buffer_name=""):
        """Reset all the interpreters for the buffer, starting completely new processes
        for them.  If buffer_name is empty the current buffer is used."""
        if buffer_name == "": buffer_name = self.lyx_process.server_get_filename()
        self.all_interps.reset_for_buffer(buffer_name)
        return

    def reset_all_interpreters_for_all_buffers(self):
        """Reset all the interpreters for all buffers, starting not-on-demand
        interpreters for the current buffer."""
        current_buffer = self.lyx_process.server_get_filename()
        self.all_interps.reset_all_interpreters_for_all_buffers(current_buffer)
        return

    def server_notify_loop(self):
        """This is the main command loop, getting commands from Lyx and executing
        them."""

        self.keymap = dict(keymap.all_commands_and_keymap) # dict mapping keys to commands

        while True:
            # Wait for a bound key in Lyx to be pressed, and get it when it is.
            key_pressed = self.lyx_process.wait_for_server_notify()
            if not key_pressed in self.keymap:
                continue # Key to ignore.

            # Eat any buffered events (notify or otherwise): avoid annoying user.
            self.lyx_process.get_server_event(info=False, error=False, notify=False)

            # Look up the action for the key.
            key_action = self.keymap[key_pressed]

            # =====================================================================
            # First, look for submenu call; open menu and reset key_action if found.
            # =====================================================================

            if key_action == "pop up submenu": # handle the pop-up menu option first
                choices = []
                for key, command in keymap.all_commands_and_keymap:
                    if key is not None:
                        key = key.replace("Shift+", "S-") # this is to align columns
                        key += " "*(5-len(key))
                    else:
                        key = " "*5
                    choices.append(key + " " + command)
                choice_str = eg.choicebox(
                    msg="Choose an action or click 'cancel'...",
                    title="LyX Notebook Submenu",
                    choices=choices,
                    sort_choices=False,
                    monospace_font=True,
                    lines_to_show=len(choices))
                if choice_str is None:
                    continue
                choice_str = choice_str[5:].strip() # EasyGUI returns whole line.
                key_action = choice_str

            # ====================================================================
            # Handle the general key actions, including commands set from submenu.
            # ====================================================================

            print("Processing user command:", key_action)
            self.lyx_process.show_message("Processing user command: " + key_action)

            #
            # Goto cell commands.
            #

            if key_action == "goto next any cell":
                self.lyx_process.open_all_cells() # gotoNextCell() needs open cells for now
                self.lyx_process.goto_next_cell()
                # self.lyx_process.goto_next_cell2() # alternate implementation, experimental

            elif key_action == "goto prev any cell":
                self.lyx_process.open_all_cells() # gotoPrevCell() needs open cells for now
                self.lyx_process.goto_prev_cell()

            elif key_action == "goto next code cell":
                self.lyx_process.open_all_cells() # gotoNextCell() needs open cells for now
                self.lyx_process.goto_next_cell(output=False)

            elif key_action == "goto prev code cell":
                self.lyx_process.open_all_cells() # gotoPrevCell() needs open cells for now
                self.lyx_process.goto_prev_cell(output=False)

            elif key_action == "goto next init cell":
                self.lyx_process.open_all_cells() # gotoNextCell() needs open cells for now
                self.lyx_process.goto_next_cell(standard=False, output=False)

            elif key_action == "goto prev init cell":
                self.lyx_process.open_all_cells() # gotoPrevCell() needs open cells for now
                self.lyx_process.goto_prev_cell(standard=False, output=False)

            elif key_action == "goto next standard cell":
                self.lyx_process.open_all_cells() # gotoNextCell() needs open cells for now
                self.lyx_process.goto_next_cell(init=False, output=False)

            elif key_action == "goto prev standard cell":
                self.lyx_process.open_all_cells() # gotoPrevCell() needs open cells for now
                self.lyx_process.goto_prev_cell(init=False, output=False)

            #
            # Ordinary cell-evaluate commands, done explicitly in Lyx.
            #

            elif key_action == "evaluate current cell":
                self.evaluate_lyx_cell()

            elif key_action == "evaluate current cell after reinit":
                print("Restarting all interpreters, single-interp restart unimplemented.")
                self.reset_interpreters_for_buffer() # TODO currently restarts them all
                self.evaluate_lyx_cell()

            elif key_action == "evaluate all code cells":
                self.evaluate_all_code_cells()

            elif key_action == "evaluate all code cells after reinit":
                self.reset_interpreters_for_buffer()
                self.evaluate_all_code_cells()

            elif key_action == "evaluate all init cells":
                self.evaluate_all_code_cells(standard=False)

            elif key_action == "evaluate all init cells after reinit":
                self.reset_interpreters_for_buffer()
                self.evaluate_all_code_cells(standard=False)

            elif key_action == "evaluate all standard cells":
                self.evaluate_all_code_cells(init=False)

            elif key_action == "evaluate all standard cells after reinit":
                self.reset_interpreters_for_buffer()
                self.evaluate_all_code_cells(init=False)

            #
            # Batch evaluation commands.
            #
            # TODO: could clean up and move bufferReplaceOnBatchEval conditionals to the
            # replaceCurrentBufferFile function (after renaming it slightly)

            elif key_action == "toggle buffer replace on batch eval":
                self.buffer_replace_on_batch_eval = not self.buffer_replace_on_batch_eval
                self.lyx_process.show_message("toggled buffer replace on batch eval to: "
                                            + str(self.buffer_replace_on_batch_eval))

            elif key_action == "revert to most recent batch eval backup":
                self.revert_to_most_recent_batch_eval_backup(messages=True)

            elif key_action == "batch evaluate all code cells":
                to_file_name = self.batch_evaluate_all_code_cells_to_lyx_file(
                    init=True, standard=True, messages=True)
                if not self.buffer_replace_on_batch_eval:
                    self.lyx_process.process_lfun("file-open", to_file_name)
                else:
                    self.replace_current_buffer_file(to_file_name,
                                                  reload_buffer=True, messages=True)

            elif key_action == "batch evaluate all code cells after reinit":
                self.reset_interpreters_for_buffer()
                to_file_name = self.batch_evaluate_all_code_cells_to_lyx_file(
                    init=True, standard=True, messages=True)
                if not self.buffer_replace_on_batch_eval:
                    self.lyx_process.process_lfun("file-open", to_file_name)
                else:
                    self.replace_current_buffer_file(to_file_name,
                                                  reload_buffer=True, messages=True)

            elif key_action == "batch evaluate all init cells":
                to_file_name = self.batch_evaluate_all_code_cells_to_lyx_file(
                    init=True, standard=False, messages=True)
                if not self.buffer_replace_on_batch_eval:
                    self.lyx_process.process_lfun("file-open", to_file_name)
                else:
                    self.replace_current_buffer_file(to_file_name,
                                                  reload_buffer=True, messages=True)

            elif key_action == "batch evaluate all init cells after reinit":
                self.reset_interpreters_for_buffer()
                to_file_name = self.batch_evaluate_all_code_cells_to_lyx_file(
                    init=True, standard=False, messages=True)
                if not self.buffer_replace_on_batch_eval:
                    self.lyx_process.process_lfun("file-open", to_file_name)
                else:
                    self.replace_current_buffer_file(to_file_name,
                                                  reload_buffer=True, messages=True)

            elif key_action == "batch evaluate all standard cells":
                to_file_name = self.batch_evaluate_all_code_cells_to_lyx_file(
                    init=False, standard=True, messages=True)
                if not self.buffer_replace_on_batch_eval:
                    self.lyx_process.process_lfun("file-open", to_file_name)
                else:
                    self.replace_current_buffer_file(to_file_name,
                                                  reload_buffer=True, messages=True)

            elif (key_action ==
                  "batch evaluate all standard cells after reinit"):
                self.reset_interpreters_for_buffer()
                to_file_name = self.batch_evaluate_all_code_cells_to_lyx_file(
                    init=False, standard=True, messages=True)
                if not self.buffer_replace_on_batch_eval:
                    self.lyx_process.process_lfun("file-open", to_file_name)
                else:
                    self.replace_current_buffer_file(to_file_name,
                                                  reload_buffer=True, messages=True)

            #
            # Misc. commands.
            #

            elif key_action == "reinitialize current interpreter":
                print("Not implemented, restarting all interpreters.")
                self.reset_interpreters_for_buffer()
                # TODO, currently restarts all: need to look up current interp
                self.lyx_process.show_message("all interpreters reinitialized")

            elif key_action == "reinitialize all interpreters for buffer":
                self.reset_interpreters_for_buffer()
                self.lyx_process.show_message("all interpreters for buffer reinitialized")

            elif key_action == "reinitialize all interpreters for all buffers":
                self.reset_all_interpreters_for_all_buffers()
                self.lyx_process.show_message(
                    "all interpreters for all buffer reinitialized")

            elif key_action == "write all code cells to files":
                file_prefix = self.lyx_process.server_get_filename()
                if file_prefix.rstrip()[-4:] != ".lyx": continue
                file_prefix = file_prefix.rstrip()[0:-4]
                data_tuple_list = []
                for spec in self.all_interps.interpreter_spec_list:
                    # currently the interactWithLyx module does not make use of any
                    # of the interpreterSpec data or its format, so we need to
                    # look some things up to pass in
                    inset_specifier = spec["inset_specifier"]
                    file_suffix = spec["file_suffix"]
                    # data tuple format is (filename, inset_specifier, commentBeginChar)
                    data_tuple_list.append((
                                         file_prefix + ".allcells." +
                                         inset_specifier + file_suffix,
                                         inset_specifier,
                                         spec["comment_line"]
                                         ))
                self.lyx_process.write_all_cell_code_to_file(data_tuple_list)
                self.lyx_process.show_message("all code cells were written to files")

            elif key_action == "insert most recent graphic file":
                self.lyx_process.insert_most_recent_graphic_as_inset()
                self.lyx_process.show_message("inserted the most recent graphic file")

            elif key_action == "kill lyx notebook process":
                sys.exit(0)

            elif key_action == "prompt echo on":
                self.no_echo = False

            elif key_action == "prompt echo off":
                self.no_echo = True

            elif key_action == "toggle prompt echo":
                self.no_echo = not self.no_echo
                message = "toggled prompt echo to " + str(not self.no_echo)
                self.lyx_process.show_message(message)

            elif key_action == "evaluate newlines as current cell":
                self.evaluate_lyx_cell(just_send_newlines=True)
                self.lyx_process.show_message("evaluated newlines as current cell")

            #
            # Commands to open and close cells.
            #

            elif key_action == "open all cells":
                self.lyx_process.open_all_cells()
                self.lyx_process.show_message("opened all cells")

            elif key_action == "close all cells":
                self.lyx_process.close_all_cells_but_current()
                self.lyx_process.show_message("closed all cells")

            elif key_action == "open all output cells":
                self.lyx_process.open_all_cells(init=False, standard=False)
                self.lyx_process.show_message("opened all output cells")

            elif key_action == "close all output cells":
                self.lyx_process.close_all_cells_but_current(init=False, standard=False)
                self.lyx_process.show_message("closed all output cells")

            else:
                pass # ignore command from server-notify if it is not recognized
        return # never executed; loop forever or sys.exit

    def evaluate_all_code_cells(self, init=True, standard=True):
        """Evaluate all cells.  Quits evaluation between cells if any Lyx Notebook
        command key is pressed (any key bound to server-notify).  The flags can
        be used to only evaluate certain types of cells."""

        # first set up code to check between cell evals whether user wants to halt

        # initialize the relevant flag in the lyxProcess class
        self.lyx_process.ignored_server_notify_event = False
        # eat any server events from Lyx (after the NOTIFY command to do the eval)
        self.lyx_process.get_server_event(info=False, error=False, notify=False)

        # define a local function to check and query the user if a NOTIFY was ignored
        def check_for_ignored_server_notify():
            """Return True if a server-notify was ignored and user wants to quit."""
            # eat all events between cell evals, and check if NOTIFY was ignored
            self.lyx_process.get_server_event(info=False, error=False, notify=False)
            if self.lyx_process.ignored_server_notify_event is True:
                msg = "Halt multi-cell evaluation at the current point?"
                choices = (["Yes", "No"])
                reply = eg.buttonbox(msg, choices=choices)
                if reply == "Yes":
                    return True
                self.lyx_process.ignored_server_notify_event = False
            return False

        # now get cell count data and print a nice message
        num_init_cells, num_standard_cells, num_output_cells = \
                                            self.lyx_process.get_global_cell_info()
        print("There are", num_init_cells+num_standard_cells, "code cells:",
              num_standard_cells, "Standard cells and", num_init_cells, "Init cells.")
        if init and standard: print("Evaluating all the code cells.")
        elif init: print("Evaluating all the Init cells only.")
        elif standard: print("Evaluating all the Standard cells only.")

        # cycle through the Init cells and then the Standard cells, evaluating
        if init:
            if num_init_cells > 0:
                self.lyx_process.goto_buffer_begin()
                self.lyx_process.open_all_cells(output=False, standard=False)
            for i in range(num_init_cells):
                user_wants_to_halt = check_for_ignored_server_notify()
                if user_wants_to_halt:
                    print("Halting multi-cell evaluation before Init cell", i+1,
                          "(a key bound to\nserver-notify was pressed).")
                    return
                self.lyx_process.goto_next_cell(output=False, standard=False)
                self.evaluate_lyx_cell()
        if standard:
            if num_standard_cells > 0:
                self.lyx_process.goto_buffer_begin()
                self.lyx_process.open_all_cells(output=False, init=False)
            for i in range(num_standard_cells):
                user_wants_to_halt = check_for_ignored_server_notify()
                if user_wants_to_halt:
                    print("Halting multi-cell evaluation before Standard cell", i+1,
                          "(a key bound to\nserver-notify was pressed).")
                    return
                self.lyx_process.goto_next_cell(output=False, init=False)
                self.evaluate_lyx_cell()
        print("Finished multi-cell evaluation.")
        return

    def batch_evaluate_all_code_cells_to_lyx_file(self, init=True, standard=True,
                                           messages=False):
        """Evaluate all the cells of the flagged basic types, and then write them
        to an output .lyx file.  The filename of the new file is returned."""
        # TODO: also could print nice message to terminal like in regular routine

        if not init and not standard: return None
        if init and not standard: cell_types = "Init"
        if not init and standard: cell_types = "Standard"
        if init and standard: cell_types = "Init and Standard"

        if messages:
            self.lyx_process.show_message("Batch evaluating all %s cells." % (cell_types,))
        # get all cell text from the Lyx auto-save file (saves it as a side effect)
        all_cells = self.lyx_process.get_all_cell_text(use_latex_export=False)

        # evaluate all the cells in the list (results pasted onto the cells)
        self.evaluate_list_of_cell_classes(all_cells, init=init, standard=standard,
                                       messages=messages)

        # get current directory data (also changes current directory to buffer's dir)
        current_dir_data = self.lyx_process.get_updated_lyx_directory_data()

        # calc the name of the auto-save file and the new .lyx file's name
        from_file_name = current_dir_data[2] # prefer auto-save file
        if from_file_name == "": from_file_name = current_dir_data[1] # buffer's file
        to_file_name = current_dir_data[3][:-4] + ".newOutput.lyx"

        # create the new .lyx file from the evaluated list of cells
        self.lyx_process.replace_all_cell_text_in_lyx_file(
            from_file_name, to_file_name, all_cells, init=init, standard=standard)

        if messages:
            self.lyx_process.show_message(
                "Finished batch evaluation of all %s cells, wait for any buffer updates."
                % (cell_types,))
        return to_file_name

    def evaluate_list_of_cell_classes(self, cell_list, init=True, standard=True,
                                  messages=False):
        """Evaluates the list of Cell class instances, first the init cells and
        then the standard cells (unless one of the flags is set False).  Used for
        batch processing and faster evaluation of a group of cells.  The resulting
        output is pasted onto the cells in cell_list as the data field
        evaluation_output.  The list cell_list is returned as a convenience."""
        msg = "Evaluating %s cell %s (%s cell)."
        if init:
            num = 0
            for cell in cell_list:
                basic_type, inset_spec = cell.get_cell_type()
                if basic_type == "Init":
                    num += 1
                    if messages:
                        self.lyx_process.show_message(msg % (basic_type, num, inset_spec))
                    self.evaluate_code_in_cell_class(cell)
            if messages:
                self.lyx_process.show_message("Finished Init cell evaluations.")
        if standard:
            num = 0
            for cell in cell_list:
                basic_type, inset_spec = cell.get_cell_type()
                if basic_type == "Standard":
                    num += 1
                    if messages:
                        self.lyx_process.show_message(msg % (basic_type, num, inset_spec))
                    self.evaluate_code_in_cell_class(cell)
            if messages:
                self.lyx_process.show_message("Finished Standard cell evaluations.")
        return cell_list

    def evaluate_lyx_cell(self, just_send_newlines=False):
        """Evaluate the code cell at the current cursor position in Lyx.  Ignore if
        not inside a code cell."""

        # get the code text from the current cell
        code_cell_text = self.lyx_process.get_current_cell_text()

        if code_cell_text is None:
            return # Not in a cell in the first place.

        # check that cell is code (could just check output=None later, but do here, too)
        basicType, inset_specifier_language = code_cell_text.get_cell_type()
        if basicType == "Output":
            return # Not a code cell.

        # TODO: optional line wrapping at the Python level (but currently works OK
        # with listings).  Currently does nothing.  Can do the same with output
        # text below, but not currently done.  Could also highlight if that
        # would display in inset and be removable for later evals.
        code_cell_text = self.wrap_long_lines(code_cell_text) # do any line-wrapping

        # do the actual code evaluation and get the output
        output = self.evaluate_code_in_cell_class(code_cell_text, just_send_newlines)

        #
        # Replace the old output with the new output (and maybe replace input).
        #

        """
        print("debug code list being replaced with:\n", code_cell_text)
        print("debug end of code list being replaced with")
        print("debug code output being replaced with:\n", output)
        print("debug end of code output being replaced with")
        """

        # Rewrite input, might be useful for wrapping or formatting.
        # Bug on rewrite with empty last line!  Empty last lines are
        # ignored by listings when saving to Latex (and sometimes in the Lyx inset).
        # Thus they are not read in correctly after having been saved, and are not
        # printed.  So perhaps better not to display them in LyX: they won't print.
        rewrite_code_cells = True
        if rewrite_code_cells and not just_send_newlines:
            self.lyx_process.replace_current_cell_text(code_cell_text, assert_inside_cell=True)
        elif not just_send_newlines:
            # some blue selection-highlighting feedback even when text not replaced...
            self.lyx_process.process_lfun("inset-select-all")
            self.lyx_process.process_lfun("escape")

        # Note there is a bug in listings 1.3 at least: showlines=true doesn't work
        # and will not show empty lines at the end of a listings box...  Adding spaces
        # or tabs on the line does not help, workaround of redefining formfeed in
        # listings is apparently blocked by passthru Flex option.  So warn users, minor
        # bug remains.
        # if len(output) > 0 and output[-1] == "\n": output[-1] = "\f\n"

        basicType, inset_specifier = code_cell_text.get_cell_type()
        self.lyx_process.replace_current_output_cell_text(output,
                      assert_inside_cell=True, inset_specifier=inset_specifier)
        return

    def evaluate_code_in_cell_class(self, code_cell_text, just_send_newlines=False):
        """Evaluate the lines of code in the Cell class instance code_cell_text.
        The output is returned as a list of lines, and is also pasted onto the
        code_cell_text instance as the data field evaluation_output.  Returns
        None for a non-code cell."""

        basicType, inset_specifier_lang = code_cell_text.get_cell_type()
        if basicType == "Output": # if not a code cell
            code_cell_text.evaluation_output = None
            return None

        # Find the appropriate interpreter to evaluate the cell.
        # Note that the inset_specifier names are required to be unique.
        interpreter_process = self.all_interps.get_interpreter_process(
                             self.lyx_process.server_get_filename(), inset_specifier_lang)
        interpreter_spec = interpreter_process.spec

        # If the interpreter_spec defines a noop_at_cell_end then append it to the cell
        # code.  Python can add "pass\n", for example, to always return to outer
        # indent level.  Most languages will define it as None.
        noop_at_cell_end = interpreter_spec["noop_at_cell_end"]
        extra_code_lines = []
        if noop_at_cell_end: # doesn't run for None or "", since they eval to False
            extra_code_lines = noop_at_cell_end.splitlines(True) # keepends=True

        # use another variable, to evaluate with modifications without changing original
        modified_code_cell_text = code_cell_text + extra_code_lines
        if just_send_newlines:
            modified_code_cell_text = ["\n", "\n"] + extra_code_lines

        # loop through each line of code, evaluating it and saving the results
        output = []
        ignore_empty_lines = interpreter_spec["ignore_empty_lines"]
        if just_send_newlines: ignore_empty_lines = False
        for code_line in modified_code_cell_text:
            #print("debug processing line:", [code_line])
            interp_result = self.process_physical_code_line(
                interpreter_process, code_line, ignore_empty_lines=ignore_empty_lines)
            #print("debug result of line:", [interp_result])
            output = output + interp_result # get the result, per line

        if len(output) > lyxNotebook_user_settings.max_lines_in_output_cell:
            output = output[:lyxNotebook_user_settings.max_lines_in_output_cell]
            output.append("<<< WARNING: Lines truncated by LyX Notebook. >>>""")

        if self.no_echo is False and interpreter_spec["prompt_at_cell_end"]:
            output.append(interpreter_process.most_recent_prompt)

        code_cell_text.evaluation_output = output
        return output

    def update_prompts(self, interp_result, interpreter_process):
        """A utility function to update prompts across interpreter evaluation
        lines.  The argument interp_result is a list of lines resulting from
        an interpreter evaluation.  This routine prepends the most recently saved
        prompt to the first command on the list, and saves the last line of the
        list as the new most recently saved prompt (to prepend next time).  Any
        autoindenting after prompts is stripped off."""
        if len(interp_result) == 0: return
        interp_result[0] = interpreter_process.most_recent_prompt + interp_result[0]
        most_recent_prompt = interp_result[-1]
        # remove any autoindent from most_recent_prompt; note main and continuation
        # prompts might have different lengths (though they usually do not)
        if most_recent_prompt.find(interpreter_process.spec["main_prompt"]) == 0:
            interpreter_process.most_recent_prompt = interpreter_process.spec["main_prompt"]
            #print("debug replaced a main prompt")
        elif most_recent_prompt.find(interpreter_process.spec["cont_prompt"]) == 0:
            interpreter_process.most_recent_prompt = interpreter_process.spec["cont_prompt"]
            #print("debug replaced a cont prompt")
        else:
            print("Warning: prompt not recognized as main or continuation prompt.")
        return interp_result[0:-1]

    def process_physical_code_line(self, interpreter_process, code_line,
                                ignore_empty_lines=True):
        """Process the physical line of code code_line in the interpreter with
        index interpIndex.  Return a (possibly empty) list of all the result lines.
        The option ignore_empty_lines ignores completely empty (all whitespace) lines,
        but not lines with comments."""

        # TODO, maybe convert any tabs to spaces in input lines

        interp_spec = interpreter_process.spec
        indent_calc = interpreter_process.indent_calc

        #print("\ndebug code_line being processed is", code_line.rstrip())

        # Ignore fully empty lines if ignore_empty_lines, but not lines with comments, etc.
        # Python interpreter actually only ends indent blocks on zero-length lines, not
        # lines with only whitespace, but those might as well be ignored, too.
        if ignore_empty_lines and len(code_line.rstrip()) == 0:
            if not indent_calc.in_string_literal():
                return []

        # update the indentation calculations for current physical line
        indent_calc.update_for_physical_line(code_line)

        # send a completely empty line if the indentation level decreased to zero
        # (uses a recursive function call which does not ignore_empty_lines)
        first_results = []
        if interp_spec["indent_down_to_zero_newline"] and indent_calc.indent_level_down_to_zero():
            first_results = self.process_physical_code_line(interpreter_process, "\n",
                                                        ignore_empty_lines=False)

        # send the line of code to the interpreter
        interpreter_process.external_interp.write(code_line)

        # get the result of interpreting the line
        interp_result = interpreter_process.external_interp.read()
        interp_result = interp_result.splitlines(True) # keepends=True

        # if the final prompt was a main prompt, not continuation, reset indent counts
        if (len(interp_result) > 0
                and interp_result[-1].rstrip() == interp_spec["main_prompt"].rstrip()
                and interp_result[-1].find(interp_spec["main_prompt"]) == 0):
            indent_calc.reset()

        # update the prompts (to remove final prompt and put prev prompt at beginning)
        interp_result = self.update_prompts(interp_result, interpreter_process)

        # if spec removeNewlineBeforePrompt is True and last line is empty, remove it
        if len(interp_result) > 0 and interp_spec["del_newline_pre_prompt"]:
            if interp_result[-1].strip() == "":
                interp_result = interp_result[:-1]

        # return the output, suppressing the first line if echo off
        # (note we're processing a physical line here, so the first line always
        # contains a prompt; even continued lines with no output have a prompt
        # line at the beginning)
        if self.no_echo and len(interp_result) > 0:
            return first_results + interp_result[1:]
        else:
            return first_results + interp_result

    def wrap_long_lines(self, line_list):
        """A stub, which later can be used to do line-wrapping on long lines,
        or modified and renamed to do any sort of processing or formatting."""
        return line_list

    def display_popup_message(self, message, text=None, seconds=3):
        """Briefly display a message in a text window.  Will use a textbox if
        text is not None, otherwise a msgbox.  This is a kludge using a fork
        to work around the limitations of EasyGUI.  BEWARE if an exit handler is
        later added... killing child might kill the running interpreters.
        Works, but is not currently used; messages are sent to the Lyx status
        bar instead."""
        newpid = os.fork()
        if newpid == 0:
            # child displays text message until killed by parent
            if text is None:
                eg.msgbox(msg=message, title="LyX Notebook", ok_button="")
            else:
                eg.textbox(msg=message, title="LyX Notebook", text=text)
            sys.exit(0) # in case user closes window before kill
        else:
            time.sleep(seconds)
            os.kill(newpid, signal.SIGHUP)
        return

    def replace_current_buffer_file(self, newfile, reload_buffer=True, messages=True):
        """Replace the current buffer file with the file newfile, saving
        a backup of the old file.  If reload_buffer=True then the Lyx buffer is
        reloaded."""
        # write out buffer if it is unsaved, before copying to backup file
        self.lyx_process.process_lfun("buffer-write", warn_error=False)

        # get the basic data
        dir_data = self.lyx_process.get_updated_lyx_directory_data(auto_save_update=False)
        num_backup_buffer_copies = lyxNotebook_user_settings.num_backup_buffer_copies

        # move the older save files down the list to make room
        for saveNum in range(num_backup_buffer_copies-1, 0, -1):
            older = ".LyxNotebookSave" + str(saveNum) + "_" + dir_data[1]
            newer = ".LyxNotebookSave" + str(saveNum-1) + "_" + dir_data[1]
            if os.path.exists(newer):
                if os.path.exists(older): os.remove(older)
                os.rename(newer, older)

        # wait for the buffer-write command started above to finish before final move
        prev_mtime = 0
        while True:
            mtime = os.stat(os.path.join(dir_data[0], dir_data[1])).st_mtime
            if mtime > prev_mtime:
                # mtime only has 1-sec resolution, so must wait over a sec...
                # could use os.path.getmtime if OS supports greater (float) resolution
                # could also check if write returned error or account for the move
                # times above to reduce the delay
                time.sleep(1.1)
                prev_mtime = mtime
            else: break

        # variable newer should have ended up at save file 0, so move buffer to that
        if os.path.exists(newer): os.remove(newer)
        os.rename(dir_data[1], newer)
        os.rename(newfile, dir_data[1])

        if reload_buffer: self.reload_buffer_file()
        if messages: self.lyx_process.show_message(
            "Replaced current buffer with newly evaluated output cells.")
        return

    def reload_buffer_file(self, dont_ask_first=True):
        """Reload the current buffer file.  If dont_ask_first is True a method is used
        which simply does the reload without asking the user."""
        if dont_ask_first:
            # This command does not ask and always reloads:
            self.lyx_process.process_lfun("vc-command", 'R $$p "/bin/echo reloading..."')
            # TODO: Bug if we do not modify file and write it back out as below!  Why?
            # Cells are not read back in right, otherwise, until a save is done.
            self.lyx_process.process_lfun("command-sequence",
                                        "self-insert x;char-delete-backward;buffer-write")
        else:
            # This LFUN will ask the user before reloading:
            self.lyx_process.process_lfun("buffer-reload")
        return

    def revert_to_most_recent_batch_eval_backup(self, messages=False):
        """Revert the most recently saved batch backup file to be current buffer."""
        # get basic data, autosaving as last resort in case this makes things worse
        dir_data = self.lyx_process.get_updated_lyx_directory_data(auto_save_update=True)
        num_backup_buffer_copies = lyxNotebook_user_settings.num_backup_buffer_copies

        most_recent_backup = ".LyxNotebookSave0_" + dir_data[1]
        most_recent_backup_full = os.path.join(dir_data[0], most_recent_backup)
        current_buffer_full = dir_data[3]

        if not os.path.exists(most_recent_backup_full):
            if messages:
                msg = "Error: No backup file to recover."
                choices = (["OK"])
                eg.buttonbox(msg, choices=choices)
                self.lyx_process.show_message(msg)
                print(msg)
            return

        back_time = time.ctime(os.stat(most_recent_backup_full).st_mtime)
        buffer_time = time.ctime(os.stat(current_buffer_full).st_mtime)

        msg = "Are you sure you want to replace the current buffer with"
        msg += " the most recent backup?"
        msg += "\nBuffer's time is:\n   " + buffer_time
        msg += "\nBackup's time is:\n   " + back_time
        choices = (["Yes", "No"])
        reply = eg.buttonbox(msg, choices=choices)
        if reply != "Yes": return

        os.remove(current_buffer_full)
        os.rename(most_recent_backup_full, current_buffer_full)

        # shift down all the older backups
        for saveNum in range(1, num_backup_buffer_copies):
            older = ".LyxNotebookSave" + str(saveNum) + "_" + dir_data[1]
            newer = ".LyxNotebookSave" + str(saveNum-1) + "_" + dir_data[1]
            if os.path.exists(older):
                if os.path.exists(newer): os.remove(newer)
                os.rename(older, newer)

        self.reload_buffer_file()
        if messages:
            msg = "Finished replacing current buffer with most recent batch backup"
            msg += " save file."
            self.lyx_process.show_message(msg)
            print(msg)
        return

#
# Testing code below, not usually run from this file as __main__.  The lyxNotebook
# script is now used to start up (after making sure another process isn't running).
#

if __name__ == "__main__":

    print("===================================================")
    print()
    print("Starting the Lyx Notebook program...")

    # start the controller

    controller = ControllerLyxWithInterpreter("lyxNotebookClient")

