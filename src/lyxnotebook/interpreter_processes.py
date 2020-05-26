"""

=========================================================================
This file is part of LyX Notebook, which works with LyX but is an
independent project.  License details (MIT) can be found in the file
COPYING.

Copyright (c) 2012 Allen Barker
=========================================================================

This file contains the class `InterpreterProcess` which holds the data
for a single interpreter process and the class `InterpreterProcessCollection`
which is a collection of interpreters.

"""

import re

from .config_file_processing import config_dict
from .external_interpreter import ExternalInterpreter, ExternalInterpreterExpect
from .interpreter_specs import process_interpreter_specs # Specs for all implemented interpreters.

USE_PEXPECT = True # Set to False to use the older approach to I/O (raw pty).

# TODO: Look into this Python library and consider if its functionality could
# replace some of this code (such as IndentCalc and the whole interpreter
# interaction stuff with pttys): https://docs.python.org/3.8/library/code.html

class IndentCalc:
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
        """The `IndentCalc` class should be sequentially passed physical lines, via
        this function."""

        # "indentation down to zero" is only considered true right after the first
        # non-continued physical line which has indentation level zero when the
        # previous line had a higher level, so always reset for each physical line.
        self.indentation_level_down_to_zero = False

        # Detect a blank line (possibly with a comment) and do nothing else.
        stripped_line = code_line.rstrip() # strip off trailing whitespace
        if len(stripped_line) == 0:
            self.backslash_continuation = False # assume blanks unset explicit continuation
            return
        first_nonwhitespace = re.search(r"\S", stripped_line)
        if first_nonwhitespace == "#":
            self.backslash_continuation = False
            return

        # Update the indentation level (unless line is continued).
        if not self.in_line_continuation():
            new_level = first_nonwhitespace.start()
            if self.indentation_level > 0 and new_level == 0:
                self.indentation_level_down_to_zero = True
            self.indentation_level = new_level

        # Backslash continuation only holds for one line (unless reset later at end)
        # this was already used in calculating self.in_line_continuation() above.
        self.backslash_continuation = False

        # Go through each char in the line, updating paren counts, etc.
        # Note that i is the index into the line stripped_line.
        backslash_escape = False
        i = -1
        while True:

            i += 1
            if i >= len(stripped_line): break
            char = stripped_line[i]

            # First handle backslash escape mode... we always ignore the next char,
            # and the only cases we care about are one-character backslash escapes
            # (let Python worry about any syntax errors with backslash outside strings).
            if backslash_escape:
                backslash_escape = False
                continue

            # Handle the backslash char, either line continuation or escape.
            if char == "\\":
                if i == len(stripped_line) - 1: # Line continuation.
                    self.backslash_continuation = True
                    continue # could also break, since at end of line
                else: # Start a backslash escape.
                    # This is only valid in strings, but let Python catch any errors there.
                    backslash_escape = True
                    continue

            # Look for string delimiters and toggle string modes.
            if char == "\"":
                # If in a string, then we got the closing quote.
                if self.in_string1: self.in_string1 = False
                # Check if this is part of a triple-quote string.
                elif (i <= len(stripped_line) - 3 and
                      stripped_line[i+1] == "\"" and stripped_line[i+2] == "\""):
                    if self.in_string2: self.in_string2 = False
                    else: self.in_string2 = True
                    i += 2 # Increment past the second two quotes of the triple-quote.
                # Otherwise we start a new single-quote string.
                else:
                    self.in_string1 = True
                continue

            # Ignore all else inside strings.
            if self.in_string_literal():
                continue

            # If at a comment begin then nothing more to do.
            if char == "#": break

            # Update counts for general delimiters.
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
            if char == ":" and not self.in_paren_bracket_curly():
                self.indentation_level += 3


class InterpreterProcess:
    """An instance of this class represents a data record for a running
    interpreter process.  Contains an `ExternalInterpreter` instance for that
    process, but also has an `IndentCalc` instance, and keeps track of the most
    recent prompt received from the interpreter."""

    def __init__(self, spec):
        """Create a data record for the given interpreter, based on the
        specification `spec`."""
        self.spec = spec
        self.most_recent_prompt = self.spec["main_prompt"]
        self.indent_calc = IndentCalc()
        if USE_PEXPECT:
            self.external_interp = ExternalInterpreterExpect(self.spec)
        else:
            self.external_interp = ExternalInterpreter(self.spec)


class InterpreterProcessCollection:
    """A class to hold multiple `InterpreterProcess` instances.  There will
    probably only be a single instance, but multiple instances should not cause
    problems.  Basically a dict that maps (bufferName,inset_specifier) tuples to
    `InterpreterProcess` class instances.  Starts processes when necessary."""

    def __init__(self, current_buffer):
        if not config_dict["separate_interpreters_for_each_buffer"]:
            current_buffer = "___dummy___" # force all to use same buffer if not set
        self.interpreter_spec_list = [specName.params
                                    for specName in process_interpreter_specs.all_specs]
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
        if not config_dict["separate_interpreters_for_each_buffer"]:
            buffer_name = "___dummy___" # Force all to use same buffer if not set.
        inset_specifier_list = [inset_specifier]
        if inset_specifier == "": # Do all if empty string.
            inset_specifier_list = self.all_inset_specifiers
        for inset_specifier in inset_specifier_list:
            key = (buffer_name, inset_specifier)
            spec = self.inset_specifier_to_interpreter_spec_dict[inset_specifier]
            if key in self.main_dict: del self.main_dict[key]
            if not spec["run_only_on_demand"]:
                self.get_interpreter_process(buffer_name, inset_specifier)

    def get_interpreter_process(self, buffer_name, inset_specifier):
        """Get interpreter process, creating/starting one if one not there already."""
        if not config_dict["separate_interpreters_for_each_buffer"]:
            buffer_name = "___dummy___" # Force all to use same buffer if not set.
        key = (buffer_name, inset_specifier)
        if key not in self.main_dict:
            msg = "Starting interpreter for " + inset_specifier
            if config_dict["separate_interpreters_for_each_buffer"]:
                msg += ", for buffer:\n   " + buffer_name
            print(msg)
            self.main_dict[key] = InterpreterProcess(
                self.inset_specifier_to_interpreter_spec_dict[inset_specifier])
        return self.main_dict[key]

    def print_start_message(self):
        """Printed out the startup message with info on the current interpreters."""
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

