"""
=========================================================================
This file is part of LyX Notebook, which works with LyX but is an
independent project.  License details (MIT) can be found in the file
COPYING.

Copyright (c) 2012 Allen Barker
=========================================================================

This module contains functions which parse and rewrite Lyx .lyx files.

"""

import copy
from .config_file_processing import config_dict
from . import gui


def get_cell_type_from_inset_begin_line(begin_line):
    """Note this depends on the naming convention in the .module files.
    Returns a tuple (<basictype>,<language>).  For example,
    ("Standard", "Python")."""
    split_line = begin_line.split(":")
    language = split_line[-1].strip()
    basic_type = split_line[-2].strip()
    return basic_type, language


class Cell:
    """Simple container class.  It holds lines of text corresponding to the
    contents of a cell as well as other data about the cell.  The line numbers
    are relative to Lyx files where the cell text is extracted.

    Cells are currently only created when parsing a Lyx string or file to
    extract the cell contents.

    The lines of Lyx-format text still have newlines on them."""

    def __init__(self, basic_type, language):
        """Initialize the data stored for the cell."""
        super().__init__()
        self.basic_type = basic_type
        self.language = language

        self.text_code_lines = [] # The lines of code in the cell, as ordinary text.
        self.has_cookie_inside = False # Is there a cookie inside this cell?
        self.evaluation_output = None # List of lines resulting from code evaluation.

        self.lyx_starting_lines = [] # The Lyx-format starting lines.
        self.starting_line_number = -1 # The line number where the cell begins.

        self.lyx_code_lines = []     # The Lyx-format code lines.

        self.lyx_ending_lines = []   # The Lyx-format ending lines.
        self.ending_line_number = -1   # The line number where the cell ends

    def get_cell_type(self):
        """Note this depends on the naming convention in the .module files.
        Returns a tuple (<basictype>,<language>).  For example,
        ("Standard", "Python")."""
        return self.basic_type, self.language

    def lyx_string_format(self, beginning=True, code=True, ending=True):
        """Return the Lyx string format of the cell, like in a .lyx file."""
        combined_list = []
        if beginning:
            combined_list += self.lyx_starting_lines
        if code:
            combined_list += self.lyx_code_lines
        if ending:
            combined_list += self.lyx_ending_lines
        return "\n".join(combined_list)

    def create_empty_cell(self):
        """Convert the cell into an empty cell of the same `basic_type` and
        `language`."""
        self.text_code_lines = []
        self.has_cookie_inside = False
        self.evaluation_output = None
        self.lyx_code_lines = []

        self.lyx_starting_lines = [
                  r"\begin_inset Flex LyxNotebookCell:{}:{}".format(
                                              self.basic_type, self.language),
                  r"status open",
                  r"",]
        self.starting_line_number = -1

        self.lyx_code_lines = []

        self.lyx_ending_lines = [r"\end_inset", r""]
        self.ending_line_number = -1

    def append(self, line):
        """Append a code line to the list."""
        self.text_code_lines.append(line)

    def copy(self):
        """Return a deep shallow copy."""
        return copy.copy(self)

    def deepcopy(self):
        """Return a deep shallow copy."""
        return copy.deepcopy(self)

    def __getitem__(self, index):
        """Index a line in the `Cell` instance."""
        # NOTE: Slices return a list, not another Cell.
        #if isinstance(index, slice):
        #    return self.lines[index.start:index.stop:index.step]
        #if index < 0: # Handle negative indices.
        #    index += len(self)
        return self.text_code_lines[index]

    def __setitem__(self, index, value):
        """Set a line in the `Cell` instance."""
        #if isinstance(index, slice):
        #    self.lines[index.start:index.stop:index.step] = value
        #    return
        #if index < 0: # Handle negative indices.
        #    index += len(self)
        self.text_code_lines[index] = value

    def __len__(self):
        return len(self.text_code_lines)

    def __repr__(self):
        all_text = "".join(self.text_code_lines)
        all_text = all_text.replace("\n", "\\n")
        basic_type, language = self.get_cell_type()
        return "Cell('{}','{}')['{}']".format(basic_type, language, all_text)


class TerminatedFile:
    """A class to read lines from a file with a known termination line, which may
    not be finished writing by a writer process.  This is to deal with possible
    race conditions.  The EOF line "" will be returned only after the file
    terminator has been seen, otherwise it will try again after a short delay.
    Also provides a pushback buffer for lookahead.  The data field number is
    incremented on each line read up to EOF (and decremented on pushback)."""

    def __init__(self, filename, termination_string, err_msg_location):
        """The `err_msg_location` string is made part of any warning message; it
        should include the name of the routine where the class instance is
        declared."""
        self.file_in = open(filename, "r")
        self.termination_string = termination_string
        self.err_location = err_msg_location
        self.buffer_lines = []
        self.found_terminator = False
        self.number = 0

    def readline(self):
        while True:
            if len(self.buffer_lines) != 0:
                line = self.buffer_lines.pop()
            else:
                line = self.file_in.readline()
            if line == "" and not self.found_terminator:
                time.sleep(0.05)
                print("Warning: read process faster than write in " + self.err_location)
                continue
            if line.rstrip() == self.termination_string:
                self.found_terminator = True
            if line != "":
                self.number += 1
            return line

    def pushback(self, line):
        if line != "":
            if line.rstrip() == self.termination_string:
                self.found_terminator = False
            self.buffer_lines.append(line)
            self.number -= 1

    def close(self):
        self.file_in.close()


def lyx_format_code_line_to_text(cell_line_list):
    """Convert the Lyx format lines in `cell_line_list` to a line in text format."""
    cell_line_substrings = []
    for line in cell_line_list:
        if line.startswith(r"\begin_inset Quotes"):
            # Lyx 2.3 introduced quote insets even inside listings; convert to '"' char.
            # The corresponding \end_inset will be ignored in condition below.
            cell_line_substrings.append('"')
        elif line.rstrip() == r"\backslash":
            cell_line_substrings.append("\\")
        elif line.startswith("\\"):
            # Skip all other markup starting with \, including `\end_inset` markers.
            # This includes anything like `\lang english` which Unicode can cause.
            pass
        else: # Got a line of actual text.
            cell_line_substrings.append(line)
    return "".join(cell_line_substrings) + "\n"


def convert_text_line_to_lyx_file_inset_format(text_line):
    """This utility function takes a single line of text as a string and returns
    a string corresponding to the Lyx file format of that line when it
    is inside a Lyx Notebook inset (i.e., in a Plain Layout block)."""
    result = "\\begin_layout Plain Layout\n"

    # Replace all backslashes with \backslash on a separate line.
    text_line_new = text_line.replace("\\", "\n\\backslash\n")

    # Split long lines at 80 chars (not quite right, compare later)
    # just try to make the diffs almost match and be a valid Lyx file.
    split_line_new = text_line_new.splitlines() # don't keep ends
    wrapped_line_new = []
    break_len = 80
    for line in split_line_new:
        while True:
            if len(line) <= break_len: # at most break_len chars in line
                wrapped_line_new.append(line + "\n")
                break

            # More than break_len chars: len(line) > break_len
            def calc_break_point(line, break_len, break_str, min_val):
                place = line[:break_len].rfind(break_str)
                if place > min_val:
                    return place
                return break_len

            break_point = min(calc_break_point(line, break_len, "\t", 70),
                              calc_break_point(line, break_len, " ", 70),
                              calc_break_point(line, break_len, ".\t", 10),
                              calc_break_point(line, break_len, ". ", 10))
            wrapped_line_new.append(line[:break_point] + "\n")
            line = line[break_point:]

    wrapped_line_new.append("\\end_layout\n\n")
    result += "".join(wrapped_line_new)
    return result


def get_text_between_input_and_output_cells(inset_specifier):
    """When creating output cells we need to insert the Lyx file code to
    create the output cell of the correct type.  This function returns
    that string text.  The `inset_specifier` is something like 'Python'."""
    st = "\\begin_inset Flex LyxNotebookCell:Output:{}\nstatus open\n"
    st = st.format(inset_specifier)
    return st


def convert_cell_lines_to_lyx_file_inset_format(cell, output_also=True):
    """Convert all the lines in the cell text to have the Lyx file inset format, to be
    written out as a .lyx file (usually after modifications to the code and/or output).
    """
    new_lines = []
    for cell_line in cell:
        new_lines.append(convert_text_line_to_lyx_file_inset_format(cell_line))
    cell[:] = new_lines # Replace the text.

    new_output_lines = []
    if output_also:
        for output_line in cell.evaluation_output:
            new_output_lines.append(convert_text_line_to_lyx_file_inset_format(output_line))
        cell.evaluation_output = new_output_lines


def get_all_lines_from_lyx_file(filename):
    """Return a list of all the lines from the Lyx file `filename`."""
    lyx_file = TerminatedFile(filename, r"\end_document",
                        err_msg_location="get_all_lines_from_lyx_file")
    line_list = []
    while True:
        line = lyx_file.readline()
        if line == "":
            break
        line_list.append(line)
    lyx_file.close()
    return line_list

    string = "".join(line_list)
    return get_all_cell_text_from_lyx_string(string,
                               magic_cookie_string, also_noncell=also_noncell)


def get_all_cell_text_from_lyx_file(filename, magic_cookie_string,
                                    code_language=None,
                                    also_noncell=False, join_char="\n"):
    """Read all the cell text from the Lyx-format string `string`."  Return a
    list of `Cell` class instances, where each cell is a list of lines (and
    some additional data) corresponding to the lines of a code cell in the
    document (in the order that they appear in the document).  All cell types
    are included.

    if `also_noncell` is true then the list returned is the list of cells
    alternating with strings holding the text in the .lyx file that is
    between the cells.
    """
    line_list = get_all_lines_from_lyx_file(filename)
    string = "".join(line_list)
    return get_all_cell_text_from_lyx_string(string,
                               magic_cookie_string, also_noncell=also_noncell)


def get_all_cell_text_from_lyx_string(lyx_string, magic_cookie_string,
                                      code_language=None,
                                      also_noncell=False):
    """Read all the cell text from the Lyx file format string `string`.  Return
    a list of `Cell` class instances, where each cell is a list of lines (and
    some additional data) corresponding to the lines of a code cell in the
    document (in the order that they appear in the document).  All cell types
    are included.

    The `code_language` option, if set, will extract only cells of the given
    language.  The string passed should be the capitalized name that appears
    at the end of the inset's name in the Lyx file, e.g., "Python".

    If `also_noncell` is true then the list returned is the list of cells
    alternating with strings holding the text in the .lyx file that is
    between the cells.
    """
    lyx_format_lines = list(reversed(lyx_string.splitlines())) # Reversed, pop off end.

    cell_list = []                   # A list of the extracted cells as `Cell` instances.
    inside_cell = False              # Inside a lyxnotebook cell of any type.
    inside_cell_plain_layout = False # Inside a Plain Layout inside a cell.
    inside_cell_text_part = False    # After the first Plain Layout inside a cell.
    text_between_cells = []
    cookie_lines_in_cells = 0
    cookie_lines_total = 0
    line_num = -1
    while True:
        if not lyx_format_lines:
            break
        lyx_line = lyx_format_lines.pop()
        line_num += 1
        rstripped_line = lyx_line.rstrip()

        # To get code cells search for lines starting with something like
        #    \begin_inset Flex LyxNotebookCell:Standard:PythonTwo
        # Those begin the inset, but individual lines of the inset are each
        # spread across several lines as substrings, between a
        # `\begin_layout Plain Layout` line and an `\end_layout` line.

        if rstripped_line.startswith(r"\begin_inset Flex LyxNotebookCell:"):
            basic_type, lang = get_cell_type_from_inset_begin_line(rstripped_line)

            # Treat cells as normal text if the language doesn't match.
            if code_language:
                if lang != code_language:
                    text_between_cells.append(lyx_line)
                    continue

            # Create a new cell.
            new_cell = Cell(basic_type, lang) # create a new cell
            new_cell.starting_line_number = line_num
            new_cell.lyx_starting_lines.append(lyx_line)

            # Save previous text between cells and reset list to empty.
            if also_noncell:
                cell_list.append("".join(text_between_cells))
            text_between_cells = []

            # Update states.
            inside_cell = True
            inside_cell_text_part = False
            inside_cell_plain_layout = False

        elif inside_cell:
            if rstripped_line == r"\end_inset":
                new_cell.lyx_ending_lines.append(lyx_line)
                new_cell.ending_line_number = line_num + 1 # Count the blank line after.

                # Read the empty line that follows an end_inset.
                next_line = lyx_format_lines.pop()
                assert next_line.rstrip() == ""
                new_cell.lyx_ending_lines.append(next_line)

                cell_list.append(new_cell) # Finished creating the cell.
                print("\noriginal text was:\n", new_cell.lyx_string_format(), sep="")

                inside_cell = False
                inside_cell_text_part = False

            elif rstripped_line == r"\begin_layout Plain Layout":
                new_cell.lyx_code_lines.append(lyx_line)
                inside_cell_plain_layout = True
                inside_cell_text_part = True

            elif inside_cell_plain_layout: # An actual line of cell text, on several lines.
                new_cell.lyx_code_lines.append(lyx_line)
                cell_line = lyx_line.rstrip("\n") # Could rstrip all whitespace.
                cell_line_list = []
                while True:
                    if cell_line.rstrip() == r"\end_layout":
                        inside_cell_plain_layout = False

                        # Read the empty line that follows an end_inset.
                        next_line = lyx_format_lines.pop()
                        assert next_line.rstrip() == ""
                        new_cell.lyx_code_lines.append(next_line)
                        break

                    next_line = lyx_format_lines.pop()
                    new_cell.lyx_code_lines.append(next_line)
                    cell_line = next_line.rstrip("\n") # drop trailing \n
                    cell_line_list.append(cell_line) # drop trailing \n
                    line_num += 1

                lyx_line = lyx_format_code_line_to_text(cell_line_list)
                cookie_find_index = lyx_line.find(magic_cookie_string)
                if cookie_find_index == 0: # Cell cookies must begin lines.
                    new_cell.has_cookie_inside = True
                    cookie_lines_in_cells += 1
                    lyx_line = lyx_line.replace(magic_cookie_string, "", 1) # Replace one occurence.
                if cookie_find_index != -1:
                    cookie_lines_total += 1

                new_cell.text_code_lines.append(lyx_line) # Got a text line, append it.

            else:
                new_cell.lyx_starting_lines.append(lyx_line)

        else: # Got an ordinary Lyx file line.
            text_between_cells.append(lyx_line)
            if lyx_line.find(magic_cookie_string) != -1: # found cookie anywhere on line
                cookie_lines_total += 1

    # Add the final text piece if `also_noncell` is true.
    if also_noncell:
        cell_list.append("".join(text_between_cells))

    # Do an error-check on the number of cookies found in the files.
    using_inset_edit_method = (config_dict["has_editable_insets_noeditor_mod"]
                               and config_dict["has_editable_insets"])
    if (using_inset_edit_method and cookie_lines_total > 0) or cookie_lines_total > 1:
        gui.text_warning_popup("Warning: Multiple cookies were found in the file.\n\n"
                            "This can cause problems with cell-goto operations.")
    if not using_inset_edit_method and cookie_lines_in_cells > 1:
        gui.text_warning_popup("Warning: Multiple cookies were found in Lyx Notebook\n"
                            "cells in the file.\n\n"
                            "This will cause problems with cell evaluations.")
    return cell_list

def replace_all_cell_text_in_lyx_string(lyx_string, replacement_cells, magic_cookie_string,
                                        code_language, init=True, standard=True):
    """Given a Lyx-format string `lyx_string` and a list of `Cell` instances
    `all_cells`, return another string in Lyx format which has the same text
    but where the content of all cells is replaced by the cells in
    `all_cells`.  Only the selected code cells are replaced.  The
    code cells are assumed to have already been evaluated with output in their
    evaluation_output data fields."""
    # TODO: not yet called anywhere...

    # TODO, consider big picture; we need text for ALL cells in output...
    # Ideally we'd only extract the particular cells to be replaced from the
    # Lyx file, easier that way, so maybe make this an all-string or all-file
    # operation, so we always do the extraction of cells right here...
    #
    # Maybe modify the extraction to take option to get corresponding output
    # files, too, if there.

    replacement_cells = list(reversed(replacement_cells)) # Reversed to pop off end.

    lyx_string_cells = get_all_cell_text_from_lyx_string(lyx_string, also_noncell=True)
    lyx_string_cells = list(reversed(lyx_string_cells)) # Reversed to pop off end.

    result_string_list = []
    while True:
        if not lyx_string_cells:
            break
        cell = lyx_string_cells.pop()
        if isinstance(cell, str):
            result_string_list.append(cell)
            continue
        basic_type, language = cell.get_cell_type()
        if language != code_language:
            continue
        if basic_type == "Init" and init or basic_type == "Standard" and standard:
            while True:
                if not replacement_cells:
                    msg = "Warning: Cells number and type do not match replacement cells."
                    print(msg)
                    gui.text_warning_popup(msg)
                replacement_cell = replacement_cells.pop()
                if isinstance(replacement_cell, str):
                    continue
                rep_basic_type, rep_language = replacement_cell.get_cell_type()
                if (rep_basic_type, rep_language) != (basic_type, language):
                    continue

                # At this point, we should have the correct replacement cell.
                replacement_string = convert_cell_lines_to_lyx_file_inset_format(
                                                               replacement_cell)
                result_string_list.append(replacement_string)

                # Now see if output cell needs replacing, too. TODO: continue here...
                #out_type, out_language = lyx_string_cells[-2].get_cell_type()
                #if out_type == "Output" and not


def replace_all_cell_text_in_lyx_file(from_file_name, to_file_name, all_cells,
                                magig_cookie_string, init=True, standard=True):
    """Given a .lyx file `from_file`, write out another .lyx file which has the
    same text but in which all cells are replaced by the cells in `all_cells`.
    Currently only the selected code cells are replaced, and the code cells
    are assumed to have already been evaluated with output in their
    evaluation_output data fields.  The corresponding output cells are always
    replaced, and created if necessary, filled with the data in that field.
    """
    # TODO: Rewrite this big ugly thing using the regular get cells but with
    # also_noncell=True.  Note, though, that this code is doing more.  It is
    # handling creating output cells if necessary, and error checks, etc.
    # Code was tested somewhat, and mostly worked, but on recent Lyx is
    # broken again.

    original_saved_lyx_file = TerminatedFile(from_file_name, r"\end_document",
                            err_msg_location="replace_all_cell_text_in_lyx_file")
    updated_saved_lyx_file = open(to_file_name, "w")
    current_cell = -1
    while True:
        line = original_saved_lyx_file.readline()
        if line == "":
            break

        elif line.find(r"\begin_inset Flex LyxNotebookCell:") != 0:
            # Got an ordinary Lyx file line, so just echo it to output
            if line.find(magic_cookie_string) != -1: # found cookie anywhere on line
                pass # later may want to do something if cookie was found
            updated_saved_lyx_file.write(line)

        else: # Got the beginning of a Flex LyxNotebookCell
            updated_saved_lyx_file.write(line) # start the new cell

            # Find out what basic type of cell it is (Init, Standard, or Output).
            if line.find(r"\begin_inset Flex LyxNotebookCell:Init") == 0:
                basic_type = "Init"
                if not init:
                    continue # just echo whole cell unless selected
            elif line.find(r"\begin_inset Flex LyxNotebookCell:Standard") == 0:
                basic_type = "Standard"
                if not standard:
                    continue # Just echo it unless selected.
            else: # Else must be an isolated output cell.
                continue # Output cells right after code cells are handed at same time.

            # Find the corresponding Cell instance in the all_cells list.
            while True:
                current_cell += 1
                bType, inset_spec = all_cells[current_cell].get_cell_type()
                if bType == basic_type:
                    break

            # Do an error check here, make sure inset_spec matches not just basic_type.
            if not (line.find(
                    r"\begin_inset Flex LyxNotebookCell:"+bType+":"+inset_spec) == 0):
                print("Error in batch evaluation, cells do not match, exiting.")
                time.sleep(4) # for xterm window displays
                sys.exit(1)

            # Echo back all cell-header stuff to out_file until a plain layout starts
            while True:
                line = original_saved_lyx_file.readline()
                if line.rstrip() == r"\begin_layout Plain Layout":
                    break
                else:
                    updated_saved_lyx_file.write(line)

            # Now eat the old cell text up to the inset end, and ignore it.
            while line.rstrip() != r"\end_inset":
                # later may want to check for cookie inside old cell
                line = original_saved_lyx_file.readline()

            # Write the new cell text (it may have been modified in processing).
            for cell_line in all_cells[current_cell]:
                updated_saved_lyx_file.write(convert_text_line_to_lyx_file_inset_format(cell_line))

            # Now end the cell in out_file.
            updated_saved_lyx_file.write("\\end_inset\n")

            # Now look ahead for an output cell; eat it all and ignore it if found.
            saved_lines = []
            while True:
                saved_lines.insert(0, original_saved_lyx_file.readline())
                # Save lines up to first non-empty, then break.
                if saved_lines[0].rstrip() != "":
                    break
            if saved_lines[0].find(
                    r"\begin_inset Flex LyxNotebookCell:Output:"+inset_spec) == 0:
                # Got an output cell, eat it.  TODO: what about math output cells?
                while True:
                    if original_saved_lyx_file.readline().rstrip() == r"\end_inset":
                        break
            else:
                # no output, pushback all saved lines
                for line in saved_lines:
                    original_saved_lyx_file.pushback(line)
            updated_saved_lyx_file.write("\n\n") # two blank lines between insets

            # Ready to write a new output cell, in both cases.
            updated_saved_lyx_file.write(
                r"\begin_inset Flex LyxNotebookCell:Output:"+inset_spec+"\n")
            updated_saved_lyx_file.write("status open\n\n") # always create an open cell
            eval_output = all_cells[current_cell].evaluation_output

            # If cell wasn't evaluated then set output to be empty.
            if eval_output is None:
                eval_output = []
            for cell_line in eval_output:
                updated_saved_lyx_file.write(convert_text_line_to_lyx_file_inset_format(cell_line))

            # Finished, end the output cell inset.
            updated_saved_lyx_file.write("\\end_inset\n") # 2 blanks pushed back from code cell end

    original_saved_lyx_file.close()
    updated_saved_lyx_file.close()

