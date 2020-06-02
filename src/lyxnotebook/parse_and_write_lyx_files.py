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
        """Return the Lyx string format of the cell.  That is, the string
        reformatted so it would be valid inside a .lyx file."""
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
        """Return a shallow copy."""
        return copy.copy(self)

    def deepcopy(self):
        """Return a deep copy."""
        return copy.deepcopy(self)

    def __getitem__(self, index):
        """Index lines in the `Cell` instance text."""
        # NOTE: Slices return a list, not another Cell.
        #if isinstance(index, slice):
        #    return self.lines[index.start:index.stop:index.step]
        #if index < 0: # Handle negative indices.
        #    index += len(self)
        return self.text_code_lines[index]

    def __setitem__(self, index, value):
        """Set a line in the `Cell` instance text."""
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
    """Convert the Lyx format lines in `cell_line_list` to a string in text format."""
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
            # This includes things like `\lang english` which Unicode can cause.
            pass
        else: # Got a line of actual text.
            cell_line_substrings.append(line)
    return "".join(cell_line_substrings) + "\n"


def convert_text_line_to_lyx_file_inset_format(text_line):
    """This utility function takes a single line of text as a string and returns
    a string corresponding to the Lyx file format of that line when it
    is inside a Lyx Notebook inset (i.e., in a Plain Layout block)."""
    result = "\\begin_layout Plain Layout\n\n"

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

    wrapped_line_new.append("\\end_layout\n")
    result += "".join(wrapped_line_new)
    return result


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


def get_all_cell_text_from_lyx_file(filename, magic_cookie_string, *,
                                    code_language=None, init=True, standard=True,
                                    also_noncell=False):
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


def get_all_cell_text_from_lyx_string(lyx_string, magic_cookie_string, *,
                                      code_language=None, init=True, standard=True,
                                      also_noncell=False):
    """Read all the code cell text from the Lyx file format string `string`.  Return
    a list of `Cell` class instances, where each cell is a list of lines (and
    some additional data) corresponding to the lines of a code cell in the
    document (in the order that they appear in the document).  All cell types
    are included by default except output cells.

    The `code_language` option, if set, will extract only cells of the given
    language.  The string passed in should be the capitalized name that appears
    at the end of the inset's name in the Lyx file, e.g., "Python".

    If `also_noncell` is true then the returned list will contain `Cell`
    instances alternating with strings holding the text in the .lyx file that
    is between the cells.  This allows the file to be put back together with
    modified cells."""
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

            # Treat cells as normal text if 1) Output cell, 2) language doesn't match,
            # 3) Basic type doesn't match.
            if code_language and lang != code_language:
                text_between_cells.append(lyx_line)
                continue
            if (basic_type=="Output" or basic_type=="Standard" and not standard
                                     or basic_type=="Init" and not init):
                text_between_cells.append(lyx_line)
                continue

            # Create a new cell.
            new_cell = Cell(basic_type, lang) # create a new cell
            new_cell.starting_line_number = line_num
            new_cell.lyx_starting_lines.append(lyx_line)

            # Save previous text between cells and reset list to empty.
            if also_noncell:
                cell_list.append("\n".join(text_between_cells))
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
                #print("\nDEBUG original text was:\n", new_cell.lyx_string_format(), sep="")

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
        cell_list.append("\n".join(text_between_cells))

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

def write_lyx_file_from_cell_list(to_file_name, all_cells):
    """Write out a .lyx file from the text in the list `all_cells`, which should
    be in the augmented format alternating cell instances and Lyx-format strings."""
    lyx_string = get_lyx_string_from_cell_list(all_cells)

    print("\n\n")
    print(lyx_string) # DEBUG
    return
    with open(to_file_name, "w") as f:
        f.write(lyx_string)

def get_lyx_string_from_cell_list(all_cells, *, replace_output_cells=True):
    """Convert the list of `Cell` instances and Lyx-format code back into a
    Lyx-format string (such as can be written to a .lyx file)."""
    lyx_pieces = []
    for c in all_cells:
        if isinstance(c, str):
            if replace_output_cells:
                c = strip_leading_output_cell(c)
            lyx_pieces.append(c)
        else:
            cell_string = get_lyx_string_from_cell(c, create_output_cell=replace_output_cells)
            lyx_pieces.append(cell_string)

    return "".join(lyx_pieces)

def strip_leading_output_cell(lyx_string):
    """Return `string` with any leading output cell stripped off."""
    lyx_string_lines = lyx_string.splitlines()
    saved_lines = []
    max_search_lines = 3
    found_cell = False
    inside_cell = False
    for count, line in enumerate(lyx_string_lines):
        if line.startswith("\\begin_inset Flex LyxNotebookCell:Output:"):
            found_cell = True
            inside_cell = True
        elif inside_cell and line.startswith(r"\end_inset"):
            inside_cell = False
        elif not inside_cell:
            saved_lines.append(line)

        if count > max_search_lines and not found_cell:
            return lyx_string # No output cell found.
    return "\n".join(saved_lines)

def get_lyx_string_from_cell(cell, create_output_cell=True):
    """Get a Lyx-format string corresponding to the code in cell `cell`  If
    `output_cell` is true then and output cell will be created if the
    cell has an evaluation string set."""
    basic_type, code_language = cell.get_cell_type()
    flex_code_start = r"\begin_inset Flex LyxNotebookCell:{}:{}".format(basic_type, code_language)
    flex_output_start = r"\begin_inset Flex LyxNotebookCell:Output:{}".format(code_language)

    lyx_pieces = [flex_code_start, "status open\n"]

    for cell_line in cell:
        lyx_pieces.append(convert_text_line_to_lyx_file_inset_format(cell_line))

    # Now end the cell.
    lyx_pieces.append("\\end_inset\n")

    # Create output cell if flagged to do so.
    if create_output_cell:
        lyx_pieces.append("\n" + flex_output_start)
        lyx_pieces.append("status open\n")

        eval_output = cell.evaluation_output
        # If cell wasn't evaluated then set output to be empty.
        if eval_output is None:
            eval_output = []

        for cell_line in eval_output:
            lyx_pieces.append(convert_text_line_to_lyx_file_inset_format(cell_line))
        lyx_pieces.append("\\end_inset\n")

    return "\n".join(lyx_pieces)

