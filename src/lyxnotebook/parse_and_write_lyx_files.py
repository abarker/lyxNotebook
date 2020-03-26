"""
=========================================================================
This file is part of LyX Notebook, which works with LyX but is an
independent project.  License details (MIT) can be found in the file
COPYING.

Copyright (c) 2012 Allen Barker
=========================================================================

This module contains functions which parse and rewrite Lyx .lyx files.

"""

from .config_file_processing import config_dict


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

            # More than break_len chars len(line) > break_len
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


def get_all_cell_text_from_lyx_file(filename, magic_cookie_string,
                                    also_noncell=False):
    """Read all the cell text from the Lyx file "filename."  Return a
    list of `Cell` class instances, where each cell is a list of lines (and
    some additional data) corresponding to the lines of a code cell in the
    document (in the order that they appear in the document).  All cell types
    are included.

    if `also_noncell` is true then the list returned is the list of cells
    alternating with strings holding the text in the .lyx file that is
    between the cells.

    To save the file and then get the most recent data from the .lyx save
    file, call get_updated_cell_text() with flag `use_latex_export=False`.
    """
    from .lyx_server_API_wrapper import Cell # Circular import if not in fun.

    saved_lyx_file = TerminatedFile(filename, r"\end_document",
                        err_msg_location="get_all_cell_text_from_lyx_file")
    cell_list = [] # A list of lines in the cell.
    inside_cell = False # Inside a lyxnotebook cell of any type.
    inside_cell_plain_layout = False # Inside a Plain Layout inside a cell.
    inside_cell_text_part = False # After the first Plain Layout inside a cell.
    text_between_cells = []
    cookie_lines_in_cells = 0
    cookie_lines_total = 0
    while True:
        line = saved_lyx_file.readline()
        rstripped_line = line.rstrip()
        if not inside_cell_text_part:
            text_between_cells.append(line)
        if line == "":
            break

        # To get code cells search for lines starting with something like
        #    \begin_inset Flex LyxNotebookCell:Standard:PythonTwo
        # Those begin the inset, but individual lines of the inset are each
        # spread across several lines as substrings, between a
        # `\begin_layout Plain Layout` line and an `\end_layout` line.
        elif rstripped_line.startswith(r"\begin_inset Flex LyxNotebookCell:"):
            inside_cell = True
            inside_cell_text_part = False
            inside_cell_plain_layout = False
            new_cell = Cell() # create a new cell
            new_cell.begin_line = line # begin{} may have meaningful args later
            new_cell.begin_line_number = saved_lyx_file.number
            # Did we find a cookie earlier that needs to be recorded with new cell?

        elif inside_cell:
            if rstripped_line == r"\end_inset":
                new_cell.end_line = line
                new_cell.end_line_number = saved_lyx_file.number
                cell_list.append(new_cell)
                text_between_cells.append(line)
                inside_cell = False
                inside_cell_text_part = False

            elif rstripped_line == r"\begin_layout Plain Layout":
                if not inside_cell_text_part:
                    del text_between_cells[-1] # Leave out this starting \begin_layout.
                if also_noncell:
                    cell_list.append("".join(text_between_cells))
                text_between_cells = []
                inside_cell_plain_layout = True
                inside_cell_text_part = True

            elif inside_cell_plain_layout: # An actual line of cell text, on several lines.
                cell_line = line.rstrip("\n") # Could rstrip all whitespace.
                cell_line_substrings = []
                while True:
                    if cell_line.rstrip() == r"\end_layout":
                        inside_cell_plain_layout = False
                        break
                    elif cell_line.startswith(r"\begin_inset Quotes"):
                        # Lyx 2.3 introduced quote insets even inside listings; convert to '"' char.
                        # The corresponding \end_inset will be ignored in condition below.
                        cell_line_substrings.append('"')
                    elif cell_line.rstrip() == r"\backslash":
                        cell_line_substrings.append("\\")
                    elif cell_line.startswith("\\"):
                        # Skip all other markup starting with \, including `\end_inset` markers.
                        # This includes anything like `\lang english` which Unicode can cause.
                        pass
                    else: # Got a line of actual text.
                        cell_line_substrings.append(cell_line)

                    cell_line = saved_lyx_file.readline().rstrip("\n") # drop trailing \n

                line = "".join(cell_line_substrings) + "\n"
                cookie_find_index = line.find(magic_cookie_string)
                if cookie_find_index == 0: # Cell cookies must begin lines.
                    new_cell.has_cookie_inside = True
                    cookie_lines_in_cells += 1
                    line = line.replace(magic_cookie_string, "", 1) # Replace one occurence.
                if cookie_find_index != -1:
                    cookie_lines_total += 1

                new_cell.append(line) # Got a line from the cell, append it.

        else: # Got an ordinary Lyx file line.
            if line.find(magic_cookie_string) != -1: # found cookie anywhere on line
                cookie_lines_total += 1

    # Add the final text piece if `also_noncell` is true.
    if also_noncell:
        cell_list.append("".join(text_between_cells))

    has_editable_insets_noeditor_mod = config_dict["has_editable_insets_noeditor_mod"]
    if (has_editable_insets_noeditor_mod and cookie_lines_total > 0) or cookie_lines_total > 1:
        gui.text_info_popup("Warning: Multiple cookies were found in the file.\n\n"
                            "This can cause problems with cell-goto operations.")
    if not has_editable_insets_noeditor_mod and cookie_lines_in_cells > 1:
        gui.text_info_popup("Warning: Multiple cookies were found in Lyx Notebook\n"
                            "cells in the file.\n\n"
                            "This will cause problems with cell evaluations.")
    return cell_list


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

