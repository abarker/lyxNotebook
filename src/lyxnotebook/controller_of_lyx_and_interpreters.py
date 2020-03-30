"""

=========================================================================
This file is part of LyX Notebook, which works with LyX but is an
independent project.  License details (MIT) can be found in the file
COPYING.

Copyright (c) 2012 Allen Barker
=========================================================================

This is the main module of the Lyx Notebook program; the entry point script
just does basic startup stuff like making sure a Lyx Notebook process is not
already running.

This module contains the implementation of the high-level controller class
`ControllerOfLyxAndInterpreters`.  This class mediates between the Lyx program
and one or more interpreters for interpreting code.  It gets basic commands
from Lyx, executes them, and pushes the appropriate actions back to Lyx.  Some
of these actions involve running code in an interpreter.  In these cases, the
controller sends the code to the appropriate interpreter, gets the results
back, and then pushes the results to Lyx.

"""

# TODO: The buffer-reload command apparently takes a parameter "dump" which causes
# it to not ask.  Maybe use that instead of current method (if still relevant).

import sys
import os
import time

from . import gui
from .config_file_processing import config_dict
from .lyx_server_API_wrapper import InteractWithLyxCells
from . import keymap # The current mapping of keys to Lyx Notebook functions.
from .parse_and_write_lyx_files import replace_all_cell_text_in_lyx_file
from .interpreter_processes import InterpreterProcess, InterpreterProcessCollection


class ControllerOfLyxAndInterpreters:
    """This class is the high-level controller class which deals with user
    interactions and which manages the Lyx process and the interpreter
    processes.  The interpreter specifications are read from the module
    `process_interpreter_specs`.  The list `process_interpreter_specs.all_specs` in
    that module is assumed to contains all the specs."""

    def __init__(self, clientname):
        """Start the controller for the client `clientname`."""

        self.no_echo = config_dict["no_echo"]
        self.buffer_replace_on_batch_eval = config_dict["buffer_replace_on_batch_eval"]

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

    def server_notify_loop(self):
        """This is the main command/event loop, getting commands from Lyx and executing
        them."""
        # Get a dict mapping keys to commands/actions.
        sleep_time = 0.25 # Time to sleep between polling, in seconds.
        self.keymap = dict(keymap.all_commands_and_keymap)
        window = None

        # Create the menu list of choices.
        menu_choices = []
        for key, command in keymap.all_commands_and_keymap:
            if key is not None:
                key = key.replace("Shift+", "S-") # this is to align columns
                key += " "*(5-len(key))
            else:
                key = " "*5
            menu_choices.append(key + " " + command)

        while True:
            # Wait for a bound key in Lyx to be pressed, and get it when it is.
            parsed_list = self.lyx_process.get_server_event(info=False, error=False)
            key_pressed = parsed_list[1].rstrip("\n") if parsed_list else None

            if key_pressed and key_pressed in self.keymap:

                # Eat any buffered events (notify or otherwise): avoid annoying user.
                self.lyx_process.get_server_event(info=False, error=False, notify=False)

                # Look up the action for the key.
                key_action = self.keymap[key_pressed]

                # Look for menu toggle; open menu if found and not already open.
                if key_action == "toggle gui": # handle the pop-up menu option first
                    if not window:
                        window = gui.main_lyxnotebook_gui_window(
                                                      menu_items_list=menu_choices)
                    else:
                        gui.close_menu(window)
                        window = None
                        continue

                self.lyx_process.show_message("Processing user command: " + key_action)
                self.respond_to_key_action(key_action)

            if window:
                choice_str = gui.read_menu_event(window, menu_choices,
                                                 timeout=0) # Time in ms.
                if choice_str:
                    if choice_str.rstrip().endswith("toggle gui"):
                        gui.close_menu(window)
                        window = None
                        continue

                    # Strip off the beginning part which shows the shortcut.
                    key_action = choice_str[5:].strip()

                    self.respond_to_key_action(key_action)

            time.sleep(sleep_time)

    def respond_to_key_action(self, key_action):
        """Perform the appropriate action for a key bound to Lyx Notebook pressed in
        the running Lyx."""
        # ====================================================================
        # Handle the general key actions, including commands set from submenu.
        # ====================================================================

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
            if file_prefix.rstrip()[-4:] != ".lyx":
                return
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

    def reset_interpreters_for_buffer(self, buffer_name=""):
        """Reset all the interpreters for the buffer, starting completely new processes
        for them.  If buffer_name is empty the current buffer is used."""
        if buffer_name == "": buffer_name = self.lyx_process.server_get_filename()
        self.all_interps.reset_for_buffer(buffer_name)

    def reset_all_interpreters_for_all_buffers(self):
        """Reset all the interpreters for all buffers, starting not-on-demand
        interpreters for the current buffer."""
        current_buffer = self.lyx_process.server_get_filename()
        self.all_interps.reset_all_interpreters_for_all_buffers(current_buffer)

    def evaluate_all_code_cells(self, init=True, standard=True):
        """Evaluate all cells.  Quits evaluation between cells if any Lyx Notebook
        command key is pressed (any key bound to server-notify).  The flags can
        be used to only evaluate certain types of cells."""

        # First set up code to check between cell evals whether user wants to halt.

        # Initialize the relevant flag in the lyxProcess class.
        self.lyx_process.ignored_server_notify_event = False
        # Eat any server events from Lyx (after the NOTIFY command to do the eval).
        self.lyx_process.get_server_event(info=False, error=False, notify=False)

        # Define a local function to check and query the user if a NOTIFY was ignored.
        def check_for_ignored_server_notify():
            """Return True if a server-notify was ignored and user wants to quit."""
            # Eat all events between cell evals, and check if NOTIFY was ignored.
            self.lyx_process.get_server_event(info=False, error=False, notify=False)
            if self.lyx_process.ignored_server_notify_event:
                msg = "Halt multi-cell evaluation at the current point?"
                reply = gui.yesno_popup(msg)
                if reply:
                    return True
                self.lyx_process.ignored_server_notify_event = False
            return False

        # Now get cell count data and print a nice message.
        num_init_cells, num_standard_cells, num_output_cells = \
                                            self.lyx_process.get_global_cell_info()
        print("There are", num_init_cells+num_standard_cells, "code cells:",
              num_standard_cells, "Standard cells and", num_init_cells, "Init cells.")
        if init and standard: print("Evaluating all the code cells.")
        elif init: print("Evaluating all the Init cells only.")
        elif standard: print("Evaluating all the Standard cells only.")

        # Cycle through the Init cells and then the Standard cells, evaluating.
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

    def batch_evaluate_all_code_cells_to_lyx_file(self, init=True, standard=True,
                                           messages=False):
        """Evaluate all the cells of the flagged basic types, and then write them
        to an output .lyx file.  The filename of the new file is returned."""
        # TODO: also could print nice message to terminal like in regular routine

        if not init and not standard:
            return None
        if init and not standard:
            cell_types = "Init"
        if not init and standard:
            cell_types = "Standard"
        if init and standard:
            cell_types = "Init and Standard"

        if messages:
            self.lyx_process.show_message("Batch evaluating all %s cells." % (cell_types,))
        # Get all cell text from the Lyx auto-save file (saves it as a side effect).
        all_cells = self.lyx_process.get_all_cell_text()

        # evaluate all the cells in the list (results pasted onto the cells)
        self.evaluate_list_of_cell_classes(all_cells, init=init, standard=standard,
                                       messages=messages)

        # Get current directory data (also changes current directory to buffer's dir).
        current_dir_data = self.lyx_process.get_updated_lyx_directory_data()

        # Calc the name of the auto-save file and the new .lyx file's name.
        from_file_name = current_dir_data[2] # prefer auto-save file
        if from_file_name == "": from_file_name = current_dir_data[1] # buffer's file
        to_file_name = current_dir_data[3][:-4] + ".newOutput.lyx"

        # Create the new .lyx file from the evaluated list of cells.
        replace_all_cell_text_in_lyx_file(
            from_file_name, to_file_name, all_cells, self.lyx_process.magic_cookie,
            init=init, standard=standard)

        if messages:
            self.lyx_process.show_message(
                "Finished batch evaluation of all {} cells, wait for any buffer updates."
                .format(cell_types))
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

    def evaluate_lyx_cell(self, rewrite_code_cell=True):
        """Evaluate the code cell at the current cursor position in Lyx.  Ignore if
        not inside a code cell or in an empty cell.

        Setting `rewrite_code_cells` false can be a little more efficient, but in case
        of bugs it gives better diagnostic information."""

        # Get the code text from the current cell.
        code_cell_text = self.lyx_process.get_current_cell_text()

        if code_cell_text is None:
            return # Not in a cell in the first place.

        # Check that cell is code (could just check output=None later, but do here, too).
        basic_type, inset_specifier_language = code_cell_text.get_cell_type()
        if basic_type == "Output":
            return # Not a code cell.

        # TODO: optional line wrapping at the Python level (but currently works OK
        # with listings).  Currently does nothing.  Can do the same with output
        # text below, but not currently done.  Could also highlight if that
        # would display in inset and be removable for later evals.
        code_cell_text = self.wrap_long_lines(code_cell_text)

        # Do the actual code evaluation and get the output.
        output = self.evaluate_code_in_cell_class(code_cell_text)

        #
        # Replace the old output with the new output (and maybe replace input).
        #

        # Rewrite input, might be useful for wrapping or formatting.
        # Bug on rewrite with empty last line!  Empty last lines are
        # ignored by listings when saving to Latex (and sometimes in the Lyx inset).
        # Thus they are not read in correctly after having been saved, and are not
        # printed.  So perhaps better not to display them in LyX: they won't print.
        cursor_after_code_inset = False
        if rewrite_code_cell:
            self.lyx_process.replace_current_cell_text(code_cell_text, assert_inside_cell=True)
        else:
            # Some blue selection-highlighting feedback even when text not replaced.
            # (The highlight doesn't appear when both are in the same command-sequence.)
            self.lyx_process.process_lfun("inset-select-all")
            self.lyx_process.process_lfun("escape") # Turn off selection.
            #cursor_after_code_inset = True # Currently doesn't work...

        # Note there is a bug in listings 1.3 at least: showlines=true doesn't work
        # and will not show empty lines at the end of a listings box...  Adding spaces
        # or tabs on the line does not help, workaround of redefining formfeed in
        # listings is apparently blocked by passthru Flex option.  So warn users, minor
        # bug remains.
        # if len(output) > 0 and output[-1] == "\n":
        #     output[-1] = "\f\n"

        basic_type, inset_specifier = code_cell_text.get_cell_type()
        self.lyx_process.replace_current_output_cell_text(output,
                      assert_inside_cell=True, inset_specifier=inset_specifier,
                      cursor_after_code_inset=cursor_after_code_inset)

    def evaluate_code_in_cell_class(self, code_cell_text):
        """Evaluate the lines of code in the `Cell` instance `code_cell_text`.
        The output is returned as a list of lines, and is also set as an
        attribute of the `code_cell_text` instance as the data field
        evaluation_output.  Returns `None` for a non-code cell."""

        basic_type, inset_specifier_lang = code_cell_text.get_cell_type()
        if basic_type == "Output": # if not a code cell
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

        modified_code_cell_text = code_cell_text.text_code_lines + extra_code_lines

        # Loop through each line of code, evaluating it and saving the results.
        output = []
        ignore_empty_lines = interpreter_spec["ignore_empty_lines"]
        for code_line in modified_code_cell_text:
            #print("debug processing line:", [code_line])
            interp_result = self.process_physical_code_line(
                interpreter_process, code_line, ignore_empty_lines=ignore_empty_lines)
            #print("debug result of line:", [interp_result])
            output = output + interp_result # get the result, per line

        if len(output) > config_dict["max_lines_in_output_cell"]:
            output = output[:config_dict["max_lines_in_output_cell"]]
            output.append("<<< WARNING: Lines truncated by LyX Notebook. >>>""")

        if not self.no_echo and interpreter_spec["prompt_at_cell_end"]:
            output.append(interpreter_process.most_recent_prompt)

        code_cell_text.evaluation_output = output
        return output

    def update_prompts(self, interp_result, interpreter_process):
        """A utility function to update prompts across interpreter evaluation
        lines.  The argument `interp_result` is a list of lines resulting from
        an interpreter evaluation.  This routine prepends the most recently saved
        prompt to the first command on the list, and saves the last line of the
        list as the new most recently saved prompt (to prepend next time).  Any
        autoindenting after prompts is stripped off."""
        if len(interp_result) == 0:
            return None
        interp_result[0] = interpreter_process.most_recent_prompt + interp_result[0]
        most_recent_prompt = interp_result[-1]
        # Remove any autoindent from most_recent_prompt; note main and continuation
        # prompts might have different lengths (though they usually do not).
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

        # Update the indentation calculations for current physical line.
        indent_calc.update_for_physical_line(code_line)

        # Send a completely empty line if the indentation level decreased to zero
        # (uses a recursive function call which does not ignore_empty_lines).
        first_results = []
        if interp_spec["indent_down_to_zero_newline"] and indent_calc.indent_level_down_to_zero():
            first_results = self.process_physical_code_line(interpreter_process, "\n",
                                                        ignore_empty_lines=False)

        # Send the line of code to the interpreter.
        interpreter_process.external_interp.write(code_line)

        # Get the result of interpreting the line.
        interp_result = interpreter_process.external_interp.read()
        interp_result = interp_result.splitlines(True) # keepends=True

        # If the final prompt was a main prompt, not continuation, reset indent counts.
        if (len(interp_result) > 0
                and interp_result[-1].rstrip() == interp_spec["main_prompt"].rstrip()
                and interp_result[-1].find(interp_spec["main_prompt"]) == 0):
            indent_calc.reset()

        # Update the prompts (to remove final prompt and put prev prompt at beginning).
        interp_result = self.update_prompts(interp_result, interpreter_process)

        # If spec removeNewlineBeforePrompt is True and last line is empty, remove it.
        if len(interp_result) > 0 and interp_spec["del_newline_pre_prompt"]:
            if interp_result[-1].strip() == "":
                interp_result = interp_result[:-1]

        # Return the output, suppressing the first line if echo off
        # (note we're processing a physical line here, so the first line always
        # contains a prompt; even continued lines with no output have a prompt
        # line at the beginning).
        if self.no_echo and len(interp_result) > 0:
            return first_results + interp_result[1:]
        return first_results + interp_result

    def wrap_long_lines(self, line_list):
        """A stub which later can be used to do line-wrapping on long lines,
        or modified (and renamed) to do any sort of processing or formatting."""
        return line_list

    def replace_current_buffer_file(self, newfile, reload_buffer=True, messages=True):
        """Replace the current buffer file with the file newfile, saving
        a backup of the old file.  If reload_buffer=True then the Lyx buffer is
        reloaded."""
        # Write out buffer if it is unsaved, before copying to backup file.
        self.lyx_process.process_lfun("buffer-write", warn_error=False)

        # Get the basic data.
        dir_data = self.lyx_process.get_updated_lyx_directory_data(
                                                              auto_save_update=False)
        num_backup_buffer_copies = config_dict["num_backup_buffer_copies"]

        # Move the older save files down the list to make room.
        for save_num in range(num_backup_buffer_copies-1, 0, -1):
            older = ".LyxNotebookSave" + str(save_num) + "_" + dir_data[1]
            newer = ".LyxNotebookSave" + str(save_num-1) + "_" + dir_data[1]
            if os.path.exists(newer):
                if os.path.exists(older):
                    os.remove(older)
                os.rename(newer, older)

        # Wait for the buffer-write command started above to finish before final move.
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
            else:
                break

        # Variable newer should have ended up at save file 0, so move buffer to that.
        if os.path.exists(newer):
            os.remove(newer)
        os.rename(dir_data[1], newer)
        os.rename(newfile, dir_data[1])

        if reload_buffer:
            self.reload_buffer_file()
        if messages:
            self.lyx_process.show_message(
                           "Replaced current buffer with newly evaluated output cells.")

    def reload_buffer_file(self, dont_ask_first=True):
        """Reload the current buffer file.  If `dont_ask_first` is true a method is used
        which simply does the reload without asking the user."""
        if dont_ask_first:
            # TODO: Try replacing this with `buffer-reload dump` which doesn't ask.
            # This command does not ask and always reloads:
            self.lyx_process.process_lfun("vc-command", 'R $$p "/bin/echo reloading..."')
            # TODO: Bug if we do not modify file and write it back out as below!  Why?
            # Cells are not read back in right, otherwise, until a save is done.
            self.lyx_process.process_lfun_seq("self-insert x",
                                              "char-delete-backward",
                                              "buffer-write")
        else:
            # This LFUN will ask the user before reloading:
            self.lyx_process.process_lfun("buffer-reload")

    def revert_to_most_recent_batch_eval_backup(self, messages=False):
        """Revert the most recently saved batch backup file to be current buffer."""
        # Get basic data, autosaving as last resort in case this makes things worse.
        dir_data = self.lyx_process.get_updated_lyx_directory_data(auto_save_update=True)
        num_backup_buffer_copies = config_dict["num_backup_buffer_copies"]

        most_recent_backup = ".LyxNotebookSave0_" + dir_data[1]
        most_recent_backup_full = os.path.join(dir_data[0], most_recent_backup)
        current_buffer_full = dir_data[3]

        if not os.path.exists(most_recent_backup_full):
            if messages:
                msg = "Error: No backup file to recover."
                gui.text_warning_popup(msg)
                self.lyx_process.show_message(msg)
                print(msg)
            return

        back_time = time.ctime(os.stat(most_recent_backup_full).st_mtime)
        buffer_time = time.ctime(os.stat(current_buffer_full).st_mtime)

        msg = "Are you sure you want to replace the current buffer with"
        msg += " the most recent backup?"
        msg += "\nBuffer's time is:\n   " + buffer_time
        msg += "\nBackup's time is:\n   " + back_time
        reply = gui.yesno_popup(msg)
        if not reply:
            return

        os.remove(current_buffer_full)
        os.rename(most_recent_backup_full, current_buffer_full)

        # Shift down all the older backups.
        for save_num in range(1, num_backup_buffer_copies):
            older = ".LyxNotebookSave" + str(save_num) + "_" + dir_data[1]
            newer = ".LyxNotebookSave" + str(save_num-1) + "_" + dir_data[1]
            if os.path.exists(older):
                if os.path.exists(newer): os.remove(newer)
                os.rename(older, newer)

        self.reload_buffer_file()
        if messages:
            msg = "Finished replacing current buffer with most recent batch backup"
            msg += " save file."
            self.lyx_process.show_message(msg)
            print(msg)

