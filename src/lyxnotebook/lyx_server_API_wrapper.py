"""
=========================================================================
This file is part of LyX Notebook, which works with LyX but is an
independent project.  License details (MIT) can be found in the file
COPYING.

Copyright (c) 2012 Allen Barker
=========================================================================

This module contains the implementation of the class `InteractWithLyxCells` which
is responsible for all interactions with the running Lyx process (via the Lyx
server).  It contains various methods for operating on cells in Lyx documents:
getting their text, operating on them, replacing them, etc.

For info on Lyx server in general, see::
   http://wiki.lyx.org/LyX/LyXServer

Note that the Lyx server accepts commands on the input pipe as ASCII text, in
the format::
       LYXCMD:clientname:function:argument
It sends back replies which have the format::
       INFO:clientname:function:data
unless there is an error, in which case the format is::
       ERROR:clientname:function:error message

The server-notify events which are sent out from Lyx only have two fields::
       NOTIFY:<key pressed>

For info on the Lyx LFUNs that can be sent over the Lyx server, see
   https://www.lyx.org/sourcedoc/latest/namespacelyx.html#a5ae63e8160e98b54ad28f142ed40c202
For similar technical notes, with raw newlines explicitly specified in the docs
where they are required (e.g. search and replace), see
   http://www.koders.com/cpp/fidB982EF8F5299023FC858C1BB857347440F3A5302.aspx?s=vector

Some earlier notes:

    Question on layouts: can one easily define separate layouts for inside insets,
    as copies of existing layouts except with different names?  If so then that
    could be used to tell exactly what sort of cell we are in, just by checking
    layout.  Can a layout be defined such that the PassThru behavior does what is
    wanted?  Note that Latex .sty style files are sometimes called layouts.  BUT,
    in Lyx .layout files are used: http://wiki.lyx.org/LyX/Concepts


    Some LFUNs which would have been useful, but currently aren't implemented in Lyx
    (rough descriptions of functionality).  These aren't meant as criticism, but just
    as a wish-list and notes about what kinds of things would have been (and still
    would be) useful.
       get-char, get-word, get-line      -- return the actual character string
       get-inset                         -- maybe get whole contents of inset as string
       export-inset, export-paragraph    -- export less than the full file
       get-position, set-position        -- cursor position in the file get or set, e.g.,
                                               <line> <char>
                                            server-get-xy does something different
       get-current-inset-type            -- the name of the inset type, i.e. Listings,
                                            or Math (like a general LFUN_IN_IPA).
       goto-next-inset <type>            -- go to next inset of that type
       inset-begin and inset-end mod     -- versions that are idempotent and stay inside
       get-lyx-version                   -- the version of Lyx in case it matters
                                              (like if new lfuns become available)
       get-lyx-dir                       -- the particular Lyx home dir
       inset-begin and inset-end         -- option to do absolute motions, regardless
                                            of the current position in the inset.

    -- Some way to dynamically set parameters on flex-insert items; maybe like the
    listings environment with "Settings" menu, even if just like the extra items
    box on the "Advanced" page with "More Parameters."  Some way to pass them as
    arguments to the flex-insert command would also be good.  (Even just
    dynamically-settable labels on Lyx Listings insets could be useful, but we
    still wouldn't have a way to inset-forall to only certain subtypes.  That would
    also need the colon-separated naming convention to be extended.  Pre- and post-
    processing could, however, be done: by redefining the Listings inset and
    changing the Latex environment name to a lstnewenvironment.)

    -- Some way to temporarily turn off user interactions, such as mouse clicks
    which can change the cursor point in the middle of other operations.  That is,
    a way to make Lyx temporarily only listen to Lyx server commands and not to
    user interactions.

    -- Some kind of "escaped passthru" might be nice, especially if things like math
    insets could be set to invoke them (and the escape char could be chosen).
    For example, allow color and style commands only.

    -- Some way to bind server-notify to menu items might be useful, so that not
    as many keys would need to be bound (especially for lesser-used functions).
    But now the gui menu does that.

    -- Some way to detect which branch you are in, or to get current branch info
    and specify branch-applicability in commands.  This might be useful, for
    example, to have a branch for code where vpython was available, and a
    branch where it wasn't.

    -- Embedded Python would also be very nice, if that ever gets included (has been
    discussed on the Lyx lists several times).  At least some kind of conditional
    structure on LFUNs might be helpful in some instances.

"""

# TODO it is probably doable to delete all magic cookies inside cells
# using lfuns.  First, detect extraneous ones.  Then, 1) goto beginning
# and 2) do word-find-forward <magicCookie> 3) test if inside a cell
# 4) if so, do char-delete-forward which should delete the full highlighted
# (char-delete-backward does the same).  5) repeat the whole process until
# it works, unless there is some way to detect failure in word-find-forward
# in which case you can just do that part again until it fails.

import sys
import os
import time
import datetime
import getpass
import random
import string # just for generating random filenames
from .config_file_processing import config_dict
from . import gui_elements as gui

# This file is repeatedly written temporarily to current dir, then deleted.
tmp_saved_lyx_file_name = "tmp_save_file_lyx_notebook_xxxxx.lyxnotebook"

class Cell(list):
    """Simple container class derived from a list.  It is meant to hold lines
    of text corresponding to the contents of a cell.  The line numbers are
    relative to Lyx/Latex files (when the cell text is extracted from such files)."""
    # TODO: maybe go back to list as internal, using composition.  Inheriting
    # from list isn't a great idea.  General list-returning operations like
    # slices return lists, not Cell subclasses.

    def __init__(self):
        """Initialize the data stored for the cell.  As a subclass of a list, the
        list elements are the lines of text."""
        # NOTE: Remember this is a list subclass with lines as elements.
        super().__init__()

        self.has_cookie_inside = False  # is there a cookie inside this cell?
        # self.lines = []  # now the base list class contains the lines
        self.begin_line_number = -1 # the line number where the cell begins
        self.begin_line = ""       # the text of the begin line (i.e., the Latex \begin)
        self.end_line_number = -1   # the line number where the cell ends
        self.end_line = ""         # the text of the end line (i.e., the Latex \end)
        self.evaluation_output = None # list of lines resulting from code evaluation

    def get_cell_type(self):
        """Note this depends on the naming convention in the .module files.
        Returns a tuple (<basictype>,<language>).  For example,
        ("Standard", "Python")."""
        if self.begin_line == -1:
            return None, None
        if self.begin_line.find(r"\begin_inset Flex LyxNotebookCell") == 0: # from Lyx
            split_line = self.begin_line.split(":")
            language = split_line[-1].strip()
            basic_type = split_line[-2].strip()
        else: # from a Latex file, \begin{...
            begin_pos = self.begin_line.find("{")+1
            end_pos = self.begin_line.find("}")
            type_string = self.begin_line[begin_pos:end_pos]
            if type_string.find("lyxNotebookCellStandard") == 0:
                language = type_string[len("lyxNotebookCellStandard"):]
                basic_type = "Standard"
            elif type_string.find("lyxNotebookCellInit") == 0:
                language = type_string[len("lyxNotebookCellInit"):]
                basic_type = "Init"
            elif type_string.find("lyxNotebookCellOutput") == 0:
                language = type_string[len("lyxNotebookCellOutput"):]
                basic_type = "Output"
            else:
                language = None
                basic_type = None
        return basic_type, language

    def __repr__(self):
        all_text = "".join(self)
        all_text = all_text.replace("\n", "\\n")
        basic_type, language = self.get_cell_type()
        return "Cell[{},{}]('{}')".format(basic_type, language, all_text)


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

class InteractWithLyxCells:
    """The main class for handling interactions with a running Lyx process
    via the Lyx server.  Also handles writing and reading data from files in
    the user's home Lyx directory."""

    def __init__(self, client_name):
        """Initialize; client_name is arbitrary but should be a unique identifier."""
        self.client_name = client_name

        # make user_name part of temp file to avoid conflicts: different users, same dir
        user_name = getpass.getuser()
        self.local_latex_filename = "zzzTmpTmp_"+user_name+"_LyxNotebook_TmpTmp.tex"

        lyx_server_pipe = config_dict["lyx_server_pipe"]
        self.lyx_server_pipe = os.path.abspath(os.path.expanduser(lyx_server_pipe))
        lyx_temporary_directory = config_dict["lyx_temporary_directory"]
        self.lyx_temporary_directory = os.path.abspath(
            os.path.expanduser(lyx_temporary_directory))

        self.lyx_server_read_event_buffer = []  # buffer for the events read from the pipe

        # a temp file is written in the Lyx temp dir
        # to avoid conflicts it uses clientname and has eight random characters added
        # (this could be improved a bit, check exists, but good enough for now)
        rnd_alphanum8 = \
            ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(8))
        self.temp_cell_write_file = self.lyx_temporary_directory + \
            "/zLyxNotebookCellTmp_" + client_name + user_name + rnd_alphanum8 + ".txt"

        self.lyx_server_pipe_in_filename = self.lyx_server_pipe + ".in"
        self.lyx_server_pipe_out_filename = self.lyx_server_pipe + ".out"

        # check that named pipes exist
        print()
        if not self.lyx_named_pipes_exist():
            print("No LyX process running (nonexistent lyxpipe file).")
            print("Start up LyX and try again.  If LyX is running, check the")
            print("lyxpipe settings in LyX and in the lyxnotebook.cfg file.")
            print()
            time.sleep(4) # pause a few seconds so xterm window displays are readable
            sys.exit(1)

        # these single file opens seem to work here, rather than repeated in processLfun
        self.lyx_server_pipe_in = os.open(self.lyx_server_pipe_in_filename, os.O_WRONLY)
        self.lyx_server_pipe_out = \
            os.open(self.lyx_server_pipe_out_filename, os.O_RDONLY | os.O_NONBLOCK)

        # empty out and ignore any existing replies or notify-events (for Lyx
        # Notebook commands) which are in the lyxServerPipeOut
        while True:
            if self.get_server_event() is None:
                break

        # Magic cookie initializations.

        # Magic cookies CANNOT contain ";" or the command-sequence LFUN will fail.
        self.magic_cookie = config_dict["magic_cookie_string"]
        cookie_len = len(self.magic_cookie)

        #self.del_cookie_forward_string = ""
        #self.del_cookie_backward_string = ""
        #self.back_cookie_string = ""
        #for i in range(0, len(self.magic_cookie)):
        #    self.del_cookie_forward_string += "char-delete-forward;"
        #    self.del_cookie_backward_string += "char-delete-backward;"
        #    self.back_cookie_string += "char-left;"
        self.del_cookie_forward_command = "repeat {} char-delete-forward;".format(cookie_len)
        self.del_cookie_backward_command = "repeat {} char-delete-backward;".format(cookie_len)

    #
    #
    # Routines for low-level communications with Lyx via the named pipes.
    #
    #

    def lyx_named_pipes_exist(self):
        """Do the special Lyx named pipe files exist?  True or False."""
        return (os.path.exists(self.lyx_server_pipe_in_filename)
                and os.path.exists(self.lyx_server_pipe_out_filename))

    def process_lfun_seq(self, *lfun_list, warn_error=True, warn_not_info=True):
        """Run all the separate commands on `lfun_list` as a command-sequence.
        No output is returned."""
        lfun_string = ";".join(lfun_list)
        self.process_lfun("command-sequence", argument=lfun_string,
                          warn_error=warn_error, warn_not_info=warn_not_info)

    def process_lfun(self, lfun_name, argument="", warn_error=True, warn_not_info=True):
        """Process the Lyx LFUN in the currently running Lyx via the server."""
        # TODO: modify to return whole parsed reply list... only a few funs all in
        # this file use the return value, and they can just bracket the third component.
        # Then we get more info on ERROR returns, etc.

        # WARNING, Unix pipes *cannot* be treated like ordinary files in Python.
        # We need to treat them like low-level OS objects and use os.open, os.read
        # and os.write on them.  We must also specify non-blocking reads.

        # First convert the command to server's protocol, then send it.
        server_protocol_string = "LYXCMD:{}:{}:{}".format(self.client_name,
                                                   lfun_name, argument + "\n")
        server_protocol_string = server_protocol_string.encode("utf-8") # for Python3
        while True:
            try:
                os.write(self.lyx_server_pipe_in, server_protocol_string)
                break
            except: # TODO what specific exceptions?
                #time.sleep(0.01)
                time.sleep(0.001)

        # Now read the reply from the output pipe, and handle ERROR cases.
        while True: # Later we may want to continue on errors below, so loop.
            parsed_list = self.wait_for_server_event(notify=False) # note NOTIFY ignored
            if warn_error and parsed_list[0] == "ERROR":
                print("Warning: Ignoring an ERROR message in processLfun(),",
                      "the parsed message list is:\n", parsed_list)
            elif warn_not_info and parsed_list[0] != "INFO":
                print("Warning: Got a non-INFO unknown reply from LyX Server" +
                      " in processLfun.  Ignoring it.")
            break
        return parsed_list[3].rstrip("\n")

    def get_server_event(self, info=True, error=True, notify=True):
        """Reads a single event from the Lyx Server.  If no event is there to
        be read it returns None.  If any flag is False then that type of event
        is completely ignored.  Returns a parsed list with the strings of the
        Lyx server events (but not the colon separator, and keeping the final
        newline on the last element in the list).

        This routine is repeated in a polling loop to wait for an event in the
        routine self.wait_for_server_event().  It can also be used outside a wait
        loop, for example, calling it with all cell types False will empty
        out all events, buffered and pending, and return None.

        If a NOTIFY event from the server is ignored it nonetheless sets the
        flag self.ignored_server_notify_event to True.  This flag can be initialized
        and accessed by a higher-level routine, if desired.  It is used to
        determine if the user hit a key bound to server-notify while some
        other actions were taking place, like a multi-cell evaluation.  The
        higher-level routine can then stop the evaluations by checking between
        cell evaluations.

        If multiple events are read at once (assumed to be delimited by newlines)
        then they are buffered and returned one at a time.
        """
        while True:
            # if no events in buffer, do a read (returning None if nothing to read)
            if len(self.lyx_server_read_event_buffer) == 0: # could be if
                if not self.lyx_named_pipes_exist():
                    print("LyX server named pipes no longer exist; LyX must have closed.")
                    print("Exiting the LyX Notebook program.")
                    time.sleep(3) # for xterm displays
                    sys.exit(0)
                try:
                    raw_reply = os.read(self.lyx_server_pipe_out, 1000)
                except:
                    return None
                # convert returned byte array to unicode string
                raw_reply = raw_reply.decode("utf-8") # for Python3 compatibility

                # check for multiple commands, assume they split on lines...
                all_events = raw_reply.splitlines()
                for event in all_events:
                    # parse the event
                    parsed_list = event.split(":", 3)
                    self.lyx_server_read_event_buffer.append(parsed_list)

            # now we know buffer is not empty, so pop an event off and analyze it
            parsed_list = self.lyx_server_read_event_buffer.pop()

            # check the type of event and compare with flags...
            if parsed_list[0] == "NOTIFY":
                if not notify:
                    self.ignored_server_notify_event = True
                    #print("debug =============================== IGNORED NOTIFY")
                    continue
                break
            elif parsed_list[0] == "ERROR":
                if not error:
                    continue
                break
            elif parsed_list[0] == "INFO":
                if not info:
                    continue
                break
            else: # ignore unknown, but print warning
                print("Warning: getServerEvent() read an unknown message type" +
                      " from LyX Server:", parsed_list)
        return parsed_list

    def wait_for_server_event(self, info=True, error=True, notify=True):
        """Go into a loop, waiting for an event from the Lyx process.  If the
        flag for any type of event is False then that type of event is ignored."""
        while True:
            parsed_list = self.get_server_event(info=info, error=error, notify=notify)
            if parsed_list is None:
                try:
                    #time.sleep(0.5) # polling, half-second response
                    time.sleep(0.25) # polling, quarter second response
                    # don't count the retries, may be polling for hours or even days
                except KeyboardInterrupt:
                    print("\nLyX Notebook exiting after keyboard interrupt.  Bye.")
                    sys.exit(0)
            else:
                break
        return parsed_list

    def wait_for_server_notify(self):
        """This routine waits for a NOTIFY event, ignoring all others.  When it
        gets one, it returns only the actual keyboard key that was pressed, with
        the trailing newline stripped.  This is called from higher-level routines
        to wait for a Lyx command-key sent by server-notify (they then to "wake up"
        and perform the action).  Thus all command-keys in Lyx for this application
        are bound to the LFUN "server-notify" (usually in a .bind file in the
        local .lyx directory)."""
        parsed_list = self.wait_for_server_event(info=False, error=False)
        # The second and last component of NOTIFY has the key:
        #   NOTIFY:<key_pressed>
        key_pressed = parsed_list[1].rstrip("\n")
        return key_pressed

    #
    #
    # Higher-level commands to perform simple tasks in Lyx.  Some just wrap LFUNs.
    #
    #

    def server_get_filename(self):
        """Return the pathname of the file being edited in the current buffer."""
        return self.process_lfun("server-get-filename")

    def server_get_layout(self):
        """Get the layout for the current cursor position."""
        return self.process_lfun("server-get-layout")

    def server_get_xy(self):
        """Get the x,y position.  Note that the top left of INSETS are always (0,0), so
        this isn't an absolute position."""
        pos = self.process_lfun("server-get-xy")
        pos = pos.split(" ")
        x = int(pos[0].strip())
        y = int(pos[1].strip())
        return x, y

    def server_set_xy(self, x, y):
        """Set the x,y position."""
        return self.process_lfun("server-set-xy", argument="{} {}".format(x,y))

    def show_message(self, string):
        """Print the message in the status bar in Lyx."""
        #self.process_lfun("message", string)
        # BUG in Lyx 2.0.3.?  Message alone doesn't show, but does as command-sequence!
        self.process_lfun("command-sequence", argument="message "+string)

    def char_left(self):
        self.process_lfun("char-left") # Don't bother returning value.

    def char_right(self):
        self.process_lfun("char-right") # Don't bother returning value.

    def inside_cell(self):
        """Are we inside a cell of the type associated with this class?  Only
        partially accurate, since it can only check the layout type and cannot
        distinguish between listings insets and custom wrapped listings insets
        (or anything else that returns "Plain Layout" from LFUN server-get-layout).
        That is, a `True` result is a necessary but not a sufficient condition."""
        return self.server_get_layout() == "Plain Layout"

    def inside_math_inset(self):
        """Test if we are inside a math inset.  Tries a math-size LFUN to see if
        it fails."""
        # Insert a math space, see if command works.  If so then in math mode
        # then delete it).
        test_string = self.process_lfun("math-space", warn_error=False, warn_not_info=False)
        inside_math = not test_string.strip() == "Command disabled"
        if inside_math:
            # Just deleting here backward doesn't always leave the cursor at the
            # very beginning, which messes up inset-select-all.
            self.process_lfun_seq("char-left", "char-delete-forward")
        return inside_math

    def goto_line_begin(self):
        """Goto the beginning of the line (stays in side inset)."""
        self.process_lfun("line-begin")

    def goto_line_end(self):
        """Goto the beginning of the line (stays in side inset)."""
        self.process_lfun("line-end")

    def at_cell_begin(self, assert_inside_cell=False):
        """Are we at the beginning of the cell, but still inside it?  The
        `assert_inside_cell` parameter can be set true when the condition is
        already known to hold, and allows an expensive Lyx server operation to
        be avoided.  (All "assert" arguments are for efficiency only, and can
        always be made False (turn off optimization) if bugs occur.)"""
        if not assert_inside_cell and not self.inside_cell():
            return False
        if True: # Faster way...
            pos = self.server_get_xy()
            return pos == (0,0)
        else:
            retval = False
            self.char_left()
            if not self.inside_cell():
                retval = True
            self.char_right() # undo the test
            return retval

    def at_cell_end(self, assert_inside_cell=False):
        """Are we at the end of the cell, but still inside it?  The
        `assert_inside_cell` parameter can be set true when the condition is
        already known to hold, and allows a Lyx server operation to
        be avoided."""
        if not assert_inside_cell and not self.inside_cell():
            return False
        if True: # Another way, not really faster.  Doesn't leave cell.
            pos = self.server_get_xy()
            self.goto_cell_end()
            pos2 = self.server_get_xy()
            retval = pos == pos2
            self.server_set_xy(*pos) # Return to original position.
        else:
            retval = False
            self.char_right()
            if not self.inside_cell():
                retval = True
            self.char_left() # undo the test
        return retval

    def inside_empty_cell(self, assert_inside_cell=False):
        """Test if we are inside an empty cell.  Assumes we are inside a cell."""
        if self.server_get_xy() != (0, 0):
            return False
        return self.at_cell_end(assert_inside_cell)
        #return (self.at_cell_begin(assert_inside_cell)
        #        and self.at_cell_end(assert_inside_cell))

    def goto_cell_end(self, assert_inside_cell=False):
        """Goes to the end of current cell.  See `goto_cell_begin` for
        more info."""
        if not assert_inside_cell and not self.inside_cell():
            return
        if True: # Faster, probably.
            self.server_set_xy(10000000, 10000000)
        else:
            self.process_lfun("repeat", argument="1000 paragraph-down")

    def goto_cell_begin(self, assert_inside_cell=False):
        """Goes to beginning of current cell.  The LFUN inset-begin works
        differently when it is already at the beginning -- it goes to the outer
        inset level.  This is modified to always stay inside (idempotent).
        Note that inset-end works similarly at the end, so can't just use that.
        The "assert_inside_cell" optional argument can speed things up just a little."""
        if not assert_inside_cell and not self.inside_cell():
            return
        if True: # Faster, probably.
            self.server_set_xy(0, 0)
        elif True:
            self.process_lfun("repeat", argument="1000 paragraph-up")
        else:
            self.process_lfun("line-begin")
            if not self.at_cell_begin(assert_inside_cell=True):
                self.process_lfun("inset-begin")

    def self_insert(self, string):
        """Inserts string at the cursor point, but cannot handle embedded newlines."""
        if string == "":
            return "empty string nothing done"
        return self.process_lfun("self-insert", string)

    def self_insert_line(self, string):
        """Adds newline after the string, but doesn't work in listings."""
        self.self_insert(string)
        return self.process_lfun("newline-insert")

    def open_all_cells(self, init=True, standard=True, output=True):
        """Open all cells of the type associated with this class.  Only implemented
        for all cells or a single type of cell being selected by flags (but could
        be extended)."""
        if init and standard and output:
            cell_type = "Flex:LyxNotebookCell"
        elif init:
            cell_type = "Flex:LyxNotebookCell:Init"
        elif standard:
            cell_type = "Flex:LyxNotebookCell:Standard"
        elif output:
            cell_type = "Flex:LyxNotebookCell:Output"
        self.process_lfun("inset-forall", cell_type+" inset-toggle open")

    def close_all_cells_but_current(self, init=True, standard=True, output=True):
        """Open all cells of the type associated with this class.  Only implemented
        for all cells or a single type of cell."""
        # could be consolidated with openAllCells() with an optional argument
        if init and standard and output:
            cell_type = "Flex:LyxNotebookCell"
        elif init:
            cell_type = "Flex:LyxNotebookCell:Init"
        elif standard:
            cell_type = "Flex:LyxNotebookCell:Standard"
        elif output:
            cell_type = "Flex:LyxNotebookCell:Output"
        self.process_lfun("inset-forall", cell_type+" inset-toggle close")

    def insert_magic_cookie_inside_current(self, on_current_line=False,
                                           assert_inside_cell=False):
        """Inserts the magic cookie into the cell.  By default the position is at
        the top left of the inset.  Using the option to put it on the current line
        saves a few operations, since we don't have to find the inset beginning,
        but the same option must also be set in cookie delete and the current line
        cannot change in the meantime (or someother assertion like undo or
        cursor-end must be made on delete)."""
        if not assert_inside_cell and not self.inside_cell():
            return None # not even in a cell, do nothing
        if on_current_line:
            self.process_lfun("line-begin")
        else:
            self.goto_cell_begin(assert_inside_cell=True)
        return self.process_lfun("self-insert", self.magic_cookie)

    def delete_magic_cookie_inside_current(self, assert_inside_cell=False,
                                 assert_cursor_at_cookie_end=False,
                                 on_current_line=False):
        """Assumes the cookie is present as the first chars of the special inset type
        (unless on_current_line is True, in which case the beginning of the current
        line is assumed).  Assertion args can be used for efficiency if the conditions
        are known to hold.  For undo to be sufficient, no intermediate actions can
        have been taken which count as changes to undo."""
        if assert_cursor_at_cookie_end:
            # Safer to not assume what a "word" is with arbitrary cookie settings...
            #return self.process_lfun("word-delete-backward")
            return self.process_lfun("command-sequence", argument=self.del_cookie_backward_command)
        if not assert_inside_cell and not self.inside_cell():
            return None # We're not even in a cell.
        if on_current_line:
            self.process_lfun("line-begin")
        else:
            self.goto_cell_begin(assert_inside_cell=True)
        self.process_lfun("command-sequence", argument=self.del_cookie_forward_command)

    def insert_magic_cookie_inside_forall(self, cell_type="Flex:LyxNotebookCell"):
        """Inserts the cookie inside all the selected insets, as beginning chars."""
        # Note that the "char-right" enters the inset.  The line-begin is important
        # in some cases (a cell starting with 'import', for example), not sure why.
        return self.process_lfun("inset-forall",
                 cell_type+" command-sequence char-right;line-begin;self-insert "+self.magic_cookie)

    def delete_magic_cookie_inside_forall(self, cell_type="Flex:LyxNotebookCell"):
        """Deletes the magic cookie from all insets, assumed inside at beginning."""
        #delString = ""
        #for i in range(0,len(self.magic_cookie)): delString += "char-delete-forward;"
        # TODO would it be possible to just globally delete the cookie from the
        # whole file?  Could do that before any operations and then afterwards to
        # avoid errors due to cookies left after errors.  LyX 2.0 now has
        # advanced search; look into that and any useful lfuns.
        return self.process_lfun("inset-forall", argument=
                # Safer to not assume what a "word" is with arbitrary cookie settings...
                #cell_type+" command-sequence char-right;word-delete-forward")
                cell_type+" command-sequence char-right;"+self.del_cookie_forward_command)

    def search_next_cookie(self):
        """Search for (goto) the next cookie in the buffer."""
        self.process_lfun("word-find-forward", self.magic_cookie)

    def search_prev_cookie(self):
        """Search for (goto) the previous cookie in the buffer."""
        self.process_lfun("word-find-backward", self.magic_cookie)

    #
    #
    # Goto operations in Lyx
    #
    #

    def goto_buffer_begin(self):
        """Goto the beginning of the document in the current buffer."""
        return self.process_lfun("buffer-begin")

    def goto_buffer_end(self):
        """Goto the end of the document in the current buffer."""
        return self.process_lfun("buffer-end")

    def goto_next_cell(self, standard=True, init=True, output=True, reverse=False):
        """Go to the next cell (of the type selected by the flags).  Currently
        only works with open cells, so the command-loop opens them all before
        calling this function.  The boolean arguments allow the type of cells
        to be chosen."""

        cell_type_list = []
        if standard:
            cell_type_list.append("Flex:LyxNotebookCell:Standard")
        if init:
            cell_type_list.append("Flex:LyxNotebookCell:Init")
        if output:
            cell_type_list.append("Flex:LyxNotebookCell:Output")
        if len(cell_type_list) == 3:
            cell_type_list = ["Flex:LyxNotebookCell"]

        for cell_type in cell_type_list:
            self.insert_magic_cookie_inside_forall(cell_type=cell_type)

        if reverse: # reverse search
            if not self.inside_cell(): self.search_prev_cookie()
            else:
                self.char_right() # char right so always find current cookie first
                self.search_prev_cookie()
                self.search_prev_cookie()
        else: # forward search
            #self.char_right() # in case at the beginning of inset, won't hurt elsewhere
            #self.search_next_cookie()
            # combine the two lines above into one server call for a bit more efficiency
            self.process_lfun("command-sequence",
                             "char-right;word-find-forward "+self.magic_cookie)
        for cell_type in cell_type_list:
            self.delete_magic_cookie_inside_forall(cell_type=cell_type)

        self.goto_cell_begin() # this also checks for inside_cell(), last may be outside

    def goto_prev_cell(self, standard=True, init=True, output=True):
        """Reverse of `goto_next_cell`."""
        self.goto_next_cell(standard=standard, init=init, output=output,
                          reverse=True)

    def server_goto_file_row(self, filename, linenum):
        r""" The line number must refer to a line in the exported Latex file in
        the Lyx temporary directory -- update if necessary using
        exportLatexToLyxTempDir().  method).  Note the numbered line must refer
        to a line of ordinary text or the line of a \begin statement for a cell
        or listing, not a line within a cell or listing environment.  Not used
        except in experimental gotoNextCell2 routine."""
        return self.process_lfun("server-goto-file-row",
                                 argument=filename + " " + str(linenum))

    def get_global_cell_info(self, use_latex_export=False):
        """This routine returns a tuple:

            num_init_cells, num_standard_cells, num_output_cells

        which is used in multiple-cell evaluations from inside Lyx.  Basically we
        need to know how many cells of each type to loop over using the cell-goto
        commands, and this function gets the data."""
        cell_list = self.get_all_cell_text(use_latex_export=use_latex_export)
        num_init_cells = 0
        num_standard_cells = 0
        num_output_cells = 0
        for cell in cell_list:
            basic_type, language = cell.get_cell_type()
            if basic_type == "Init":
                num_init_cells += 1
            elif basic_type == "Standard":
                num_standard_cells += 1
            elif basic_type == "Output":
                num_output_cells += 1
        return num_init_cells, num_standard_cells, num_output_cells

    #
    #
    # Operations to get and modify text in cells.
    #
    #

    def get_all_cell_text(self, use_latex_export=False,
                          nodelete_tmpfile=False,
                          also_noncell=False):
        """Returns a list of `Cell` data structures containing the text for each
        cell in the current buffer.  Always updates the file before reading it.
        It can read either from a locally exported .tex Latex file (with
        use_latex_export=True) or from a Lyx-format file saved temporarily to
        the current directory.  The Lyx-format version is currently preferred,
        and the older Latex version may now need minor fixes."""

        # Note getUpdatedLyxDirectoryData changes current dir to buffer's dir.
        (bufferDirName,
         bufferFileName,
         autoSaveFileName,
         full_path) = self.get_updated_lyx_directory_data()

        if use_latex_export: # May not work anymore...
            return self.get_all_cell_text_via_latex_file(bufferDirName)
        return self.get_all_cell_text_via_lyx_file(bufferDirName,
                                              nodelete_tmpfile=nodelete_tmpfile,
                                              also_noncell=also_noncell)

    #
    # Get cell and modify cell info from the Lyx source file.
    #

    def get_all_cell_text_via_lyx_file(self, bufferDirName,
                                       also_noncell=False,
                                       nodelete_tmpfile=False):
        """Get all Lyx cell text using the method of writing and parsing the `.lyx`
        file."""
        # Export temporarily to a local file.
        full_tmp_name = os.path.join(bufferDirName, tmp_saved_lyx_file_name)
        self.process_lfun("buffer-export-custom",
                         "lyx mv $$FName " + full_tmp_name, warn_error=True)
        time.sleep(0.05) # let write get a slight head start before any reading
        all_cells = self.get_all_cell_text_from_lyx_file(full_tmp_name,
                                                    self.magic_cookie,
                                                    also_noncell=also_noncell)
        if not nodelete_tmpfile and os.path.exists(tmp_saved_lyx_file_name):
            os.remove(tmp_saved_lyx_file_name)
        return all_cells

    @staticmethod
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

    @staticmethod
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

    def get_updated_lyx_directory_data(self, auto_save_update=False):
        """
        This function returns a tuple of the form:
           (<currentBufferFileDirectory>,<currentBufferFilename>,
           <auto-saveFilename>, <currentBufferFullPath>)
        It tries to save an auto-save file (unless auto_save_update is False), and
        returns "" for the auto-save file if the file still does not exist.
        """
        # get the ordinary pathname and directory name of the buffer file
        fullpath = self.server_get_filename()
        dirname = os.path.dirname(fullpath)
        basename = os.path.basename(fullpath)

        # Change directory (the document in the current buffer may change, new dir)
        #os.chdir(dirname) # TODO: Avoid this if possible; delete if no problems.

        # try a save to auto-save file, then check if one exists newer than basename
        # (latter check needed for initial files which haven't been changed)
        if auto_save_update:
            self.process_lfun("buffer-auto-save")
        auto_save_filename = "#" + basename + "#"
        if not os.path.exists(auto_save_filename):
            auto_save_filename = ""
        elif (os.path.exists(basename)
              and os.stat(auto_save_filename).st_mtime < os.stat(basename).st_mtime):
            print("Warning: auto-save file older than buffer file, not using it.")
            auto_save_filename = ""

        # return the tuple
        return dirname, basename, auto_save_filename, fullpath

    #
    # Get and modify text in the current cell.
    #

    def get_current_cell_text(self, use_latex_export=False):
        r"""Returns a `Cell` data structure containing the current text of the cell,
        as lines.  Returns `None` if the cursor is not currently inside a cell
        or if the cell is empty.

        The \begin and \end Latex markers (or Lyx markers) for the cell type are not
        included as lines of a Cell, but they are saved as additional fields.
        This currently works by putting a cookie in the current cell, updating the
        save/export, removing the cookie, and then reading all the cells in from
        that file and looking for which one has the cookie.  (This routine is
        nontrivial due to a lack of LFUNs to do it more directly.)"""
        # This routine is similar to `get_all_cell_text()` except the current cell has
        # to be singled out (identified with a cookie).  It calls that routine
        # after setting the cookie, searches for it, then deletes the cookie.
        if not self.inside_cell() or self.inside_empty_cell(assert_inside_cell=True):
            return None # return None if not in a cell or empty cell

        has_editable_insets_noeditor_mod = config_dict["has_editable_insets_noeditor_mod"]
        has_editable_insets = config_dict["has_editable_insets"]

        if has_editable_insets and has_editable_insets_noeditor_mod:
            # TODO: Later maybe implement searching for the file from unmodified inset-edit.

            # Get all the cells from the Lyx or Latex output, because we need to
            # know the language associated with the current cell.  We will compare
            # text.
            all_cells = self.get_all_cell_text(use_latex_export=use_latex_export,
                                               also_noncell=False)
            # set above also_noncell to use below debug code; delete later.
            """
            with open("zzzzz_lyxnotebook_tmp_debug.lyxnotebook", "w") as f:
                for i in all_cells: # DEBUG XXX
                    if isinstance(i, str):
                        print(i, end="", file=f) # DEBUG
                    else:
                        print(i, "\n\n", end="", sep="", file=f) # DEBUG
            all_cells = [c for c in all_cells if not isinstance(c, str)] # DEBUG XXX
            """

            # Get the text from the current cell.
            # Note below, we cannot enter cells with open edits, anyway...
            #self.process_lfun("inset-end-edit") # In case there was an open edit already.
            filename = self.process_lfun("inset-edit", argument="noeditor")
            if filename == "Command disabled":
                print("Warning: Lyx Notebook attempted to run 'inset-edit' in a "
                        "context where the command is disabled.")
                return None
            try:
                with open(filename, "r") as f:
                    cell_text = f.readlines()
            except FileNotFoundError:
                print("Warning: Lyx Notebook could not write out the .lyx file '{}'".
                        format(filename))
                return None
            if cell_text[-1][-1] != "\n":
                cell_text[-1] += "\n" # Needed for cells with no blank lines at the end.

            # TODO OPT: word-right below would skip a few steps in
            # `replace_current_output cells`, but that routine is called from
            # `evaluate_lyx_cell`, which would need the option
            # `rewrite_code_cells` made false.  Using word-right leaves cursor
            # just after the inset, and using char-right leaves it inside the
            # inset.
            self.process_lfun_seq("inset-end-edit", "char-right")

            cell_match_indices = []
            for count, cell in enumerate(all_cells):
                basic_type, language = cell.get_cell_type()
                if basic_type not in ["Standard", "Init"]:
                    continue
                lines_match = True
                for target_line, line in zip(cell_text, cell):
                    if target_line != line:
                        lines_match = False
                        break
                if lines_match:
                    cell_match_indices.append(count)
            if not cell_match_indices:
                gui.text_info_popup(
                       "Warning: No cells in the .lyx file matched the text extracted\n"
                       "from the inset via the inset-edit LFUN.")
                return None
            if len(cell_match_indices) > 1:
                first_match = all_cells[cell_match_indices[0]]
                # Empty cells don't reach here as of now, but line below checks anyway.
                if len(first_match) != 1 or first_match[0] != "": # If cells not empty.
                    languages = {all_cells[i].get_cell_type()[1]
                                                       for i in cell_match_indices}
                    msg = ("Warning: Cell numbered {} contain identical code for \n"
                          "different languages.  Don't know which interpreter to run..."
                          .format(cell_match_indices))
                    if len(languages) != 1:
                        print(msg)
                        gui.text_info_popup(msg)
                        return None
            matched_index = cell_match_indices[0]
            return all_cells[matched_index]

        else: # Don't have modified inset-edit, use the older magic cookie way.
            self.insert_magic_cookie_inside_current(assert_inside_cell=True,
                                                    on_current_line=False)

            all_cells = self.get_all_cell_text(use_latex_export=use_latex_export)

            self.delete_magic_cookie_inside_current(assert_cursor_at_cookie_end=True)

            found_cookie = False
            for cell in all_cells:
                if cell.has_cookie_inside:
                    if found_cookie:
                        err_msg = ("\n\nWARNING: multiple cells have cookies inside them."
                              "\nNot performing the operation.  Globally delete the"
                              "\ncookie string " + self.magic_cookie + " from the"
                              " document and try again.\n")
                        print(err_msg, file=sys.stderr)
                        gui.text_info_popup(err_msg)
                        return None
                    found_cookie = True
                    return_cell = cell
            # return Cell() # Was causing bugs in ordinary Listings cells, now return None.
            if found_cookie:
                return return_cell
            return None

    def replace_current_output_cell_text(self, line_list, create_if_necessary=True,
               goto_begin_after=False, assert_inside_cell=False, inset_specifier="Python",
               cursor_after_code_inset=False):
        """Replace the text of the output cell corresponding to the current `Standard`
        or `Init` cell.  The cell should immediately follow.  If it doesn't and
        `create_if_necessary` is true then an output cell will be created/inserted.  The
        default is a Python cell; this can be changed by setting `inset_specifier` to a
        value from one of the other interpreter specs.

        The cursor is assumed to be inside the code inset.  If `cursor_after_code_inset`
        is true the cursor is assumed to be just after the code inset."""
        if not assert_inside_cell and not self.inside_cell():
            return # Not even in a cell.

        # First we run a big command-sequence to do the following:
        # -- use inset-select-all and two escapes to leave the inset (first escape
        #    turns off any selections to ensure that the second always exits the inset)
        # -- word-backward to goto before the inset, then try to open it in case it
        #    is closed (newly inserted cells are closed, inconvenient and causes probs
        #    problems at EOF) then word-forward to go back to after the inset
        # -- inset-toggle open to open any output cell which might be there (if
        #    there is one and it is closed we can't move inside it in next step)
        # -- go right one char (to prepare to test if an inset immediately follows,
        #    since we will be inside cell if there is one).
        #
        # (For some reason in 2.0.3 the inset-select-all doesn't gives the nice blue
        # selection-highlighting feedback when called this way, so it is added
        # in the evaluateCell routine if text in code cells isn't replaced.)
        if cursor_after_code_inset:
            # TODO, this option isn't working right for some reason.
            # It isn't entering the output cell (if there).
            self.process_lfun("inset-toggle-open") # Run alone because can be ERROR?
            self.process_lfun("char-right")
        else: # Cursor is inside the inset.
            self.process_lfun_seq("inset-select-all", # Select all.
                                  "escape", # This turns off selection.
                                  "escape", # This leaves the inset to the right.
                                  "word-backward", # Goto before inset.
                                  "inset-toggle open", # Open the inset.
                                  "word-forward", # Goto after inset.
                                  "inset-toggle open", # Open output inset if there.
                                  "char-right") # Enter the output inset if there.

        # Check if there is a math inset just after the code inset.
        if self.inside_math_inset():
            self.process_lfun_seq("inset-select-all")
            # Delete all text in existing inset, so we know it is empty.
            line_list = [li.strip("\n") for li in line_list] # Only a single line allowed.
            line_string = "".join(line_list)
            self.process_lfun("math-insert", argument=line_string)
            return

        # At this point, if there is an inset immediately afterward we are
        # inside it.  Now test if we are inside a Lyx Notebook cell, assumed to
        # be the output cell if so.
        empty_cell = False
        if not self.inside_cell(): # No output cell immediately follows.
            if create_if_necessary: # Create a new output cell.
                self.char_left() # Undo char-right in test above (end just outside cell).
                # The line below handles the special case of end of buffer insert.
                if self.inside_cell():
                    self.char_right()
                # Now insert the output cell.
                # Note that flex-insert adds the "Flex:" prefix on the cell name.
                # Note this puts you inside the new Flex cell (so inset-toggle-open may
                #    be unnecessary).
                self.process_lfun_seq("flex-insert LyxNotebookCell:Output:"+inset_specifier,
                                      "inset-toggle open")
                empty_cell = True
            else:
                # If we don't create a new cell, go back inside the previous cell.
                self.char_left()
                if not self.inside_cell():
                    self.char_left() # Handles end of buffer, too.

                # Note we currently stay inside the inset but at the end.
                return

        # After this point, we know we are inside the output cell.
        #self.server_set_xy(1, 0) # Move cursor to optimize later inside_empty_cell call.
        self.goto_cell_end() # Move cursor to optimize later inside_empty_cell call.

        # Note this test and `empty_cell` flag was added in Mar. 2017 to fix
        # bug that was introduced by a change in how Lyx handles the
        # "select-all" command in an empty cell (don't know version).  It now
        # selects the whole cell, which then gets replaced.  So if empty we are
        # inside and don't need to select anything since there is nothing to
        # replace.
        if not empty_cell and self.inside_empty_cell():
            empty_cell = True

        self.replace_current_cell_text(line_list, assert_inside_cell=True,
                                                  empty_cell=empty_cell)
        if goto_begin_after:
            self.goto_cell_begin(assert_inside_cell=True)

    def replace_current_cell_text(self, line_list,
                               goto_begin_after=False, assert_inside_cell=False,
                               empty_cell=False):
        r"""Replace the current cell's text with the lines in `line_list`
        Currently `line_list` can be a `Cell` instance, but it can also just be a list
        since no special `Cell` extra data is used.  The lines in `line_list` must be
        newline terminated, but should not include any `\begin` and `\end` Latex
        markup lines for the cell type."""
        # Write the text to a file and then read it in all at once, replacing
        # selected text.  This gives better undo behavior than a self-insert
        # for each line.

        if not assert_inside_cell and not self.inside_cell():
            return # Not even in a cell.

        if len(line_list) == 0:
            line_list = [""] # Cells always have at least one line.

        with open(self.temp_cell_write_file, "w") as f:
            # Process all but the last line (we know it has at least one).
            if len(line_list) > 1:
                for line in line_list[0:-1]:
                    f.write(line)

            # Process the last line; strip off the newline so it displays right when read in.
            stripped_last_line = line_list[-1].rstrip("\n") # debug changed from plain strip
            delete_space = False
            if stripped_last_line == "": # We cannot write and read a single empty string,
                stripped_last_line = " " # so write a space, to delete later.
                delete_space = True

            f.write(stripped_last_line)

        # Read file into lyx, deleting space if it was inserted in special case above.
        self.replace_current_cell_text_from_plaintext_file(self.temp_cell_write_file,
                                                 assert_inside_cell=assert_inside_cell,
                                                 empty_cell=empty_cell)
        if delete_space:
            self.process_lfun("char-delete-backward")

        # Clean up by deleting the temporary file.
        os.remove(self.temp_cell_write_file)
        if goto_begin_after:
            self.goto_cell_begin(assert_inside_cell=True)

    def replace_current_cell_text_from_plaintext_file(self, filename,
                                     assert_inside_cell=False, empty_cell=False):
        """Replaces the cell's text with the contents of file filename."""
        if not assert_inside_cell and not self.inside_cell():
            return

        # Select everything in the inset, to be replace by the file-insert.
        if not empty_cell:
            self.process_lfun("inset-select-all")

        # Read in the file, replacing selected text.
        # self.process_lfun("file-insert-plaintext-para", filename) # ignores newlines!
        self.process_lfun("file-insert-plaintext", filename)

    def write_all_cell_code_to_file(self, data_tuple_list):
        """Sequentially writes all the cell code to output files, with cells of
        each inset_specifier type being written to a different file, and where the
        init cells are written before the standard cells.  The format for
        data_tuple_list is a list of tuples of the form

           (filename, inset_specifier, commentLineBegin)

        The calling routine should figure out the dataTuple information, since
        this module does not have access to interpreterSpec data.  Currently
        will silently overwrite filename.  If comment-line char is set to a
        non-empty value then extra information to be written to the file in
        comments."""
        (currentBufferFileDirectory,
         currentBufferFilename,
         auto_save_filename,
         full_path) = self.get_updated_lyx_directory_data()

        # Get all the cells and open the file with name filename.
        all_cells = self.get_all_cell_text()
        # some test lines for debugging below
        #all_cells = self.get_all_cell_text_from_latex(mostRecentLatexExport)
        #all_cells = self.get_all_cell_text_from_lyx_file(currentBufferFilename, self.magic_cookie)

        # Loop through all the inset types, writing the cells for that type.
        for filename, inset_specifier, commentLineBegin in data_tuple_list:

            # don't write if no cells of the particular type
            cells = [c for c in all_cells if c.get_cell_type()[1] == inset_specifier]
            if len(cells) == 0:
                continue

            # Write an informative header comment to the file.
            with open(filename, "w") as code_out_file:
                banner_line = commentLineBegin + "="*70
                now = datetime.datetime.now()
                if commentLineBegin: # Don't write if commentLineBegin string is empty.
                    code_out_file.write("\n" + banner_line + "\n")
                    msg = commentLineBegin + " File of all " + inset_specifier \
                        + " cells from LyX Notebook source file:\n" \
                          + commentLineBegin + "    " + currentBufferFilename + "\n" \
                          + commentLineBegin + " " + now.strftime("%Y-%m-%d %H:%M")
                    code_out_file.write(msg)
                    code_out_file.write("\n" + banner_line + "\n\n")

                # Write the cells of the inset_specifier type to the file.
                for basic_cell_type in ["Init", "Standard"]:
                    count = 0
                    for cell in all_cells:
                        cell_type = cell.get_cell_type()
                        if cell_type[0] == basic_cell_type and cell_type[1] == inset_specifier:
                            count += 1
                            if commentLineBegin: # Don't write if empty commentLineBegin string.
                                code_out_file.write("\n" + banner_line + "\n")
                                msg = commentLineBegin + " " + basic_cell_type + \
                                    " cell number " + str(count) + "."
                                code_out_file.write(msg)
                                code_out_file.write("\n" + banner_line + "\n\n")
                            for line in cell:
                                code_out_file.write(line)

    #
    # Create graphics insets.
    #

    def insert_most_recent_graphic_as_inset(self):
        """Find the most recent graphics file in the current buffer's directory
        and insert it as a graphics inset at the current Lyx cursor point."""
        # general data about file suffixes recognized as graphics formats
        graphic_extensions = ".emf,.eps,.jpeg,.jpg,.pdf,.png,.ps,.raw,.rgba,.svg,.svgz"

        # get the dir of the current buffer and change directories to it
        dir_data = self.get_updated_lyx_directory_data(auto_save_update=False)

        # find most recent graphics file
        max_mtime = 0
        most_recent = ""
        for dirpath, subdirs, files in os.walk(dir_data[0]):
            for fname in files:
                fnameRoot, extension = os.path.splitext(fname)
                if extension not in graphic_extensions:
                    continue
                full_path = os.path.join(dirpath, fname)
                mtime = os.stat(full_path).st_mtime # or can use os.path.getmtime()
                if mtime > max_mtime:
                    max_mtime = mtime
                    # set most_recent to path relative to current dir, for portability
                    most_recent = os.path.relpath(full_path)

        # old implementation in comment-string below works, not as portable, Unix-based
        """
        # Note the last char in options to ls is the number 1, not the letter l.
        lsCmd = r"ls -ct1 *.{" + graphicFormats + "} 2>/dev/null"
        f = os.popen(lsCmd)
        most_recent = f.readline().strip() # get first listed, strip off whitespace (\n)
        """

        if most_recent == "":
            print("No graphics files found in current directory!")
            return
        print("Inserting inset for most recent graphics file, " + most_recent +
              ", at the cursor point (assuming the operation is allowed).")
        # could set height, too, but may affect aspect ratio
        # lyxscale is the percent scaling of the display in Lyx
        graph_str = r"graphics lyxscale 100 width 5in keepAspectRatio filename " \
            + most_recent
        self.process_lfun("inset-insert", graph_str)

    #
    # Get cell info by writing and analyzing the Latex source file.
    # TODO: This method may or may not still work...
    #

    def get_all_cell_text_via_latex_file(self, bufferDirName):
        """Get all Lyx cell text using the method of parsing the `.lyx` file."""
        # Export to local Latex file, and wait only briefly
        # TODO can use full_path now instead of re-join
        abs_local_file_path = os.path.join(bufferDirName, self.local_latex_filename)
        if os.path.exists(abs_local_file_path):
            os.remove(abs_local_file_path)
        self.export_latex_to_file(abs_local_file_path)
        while not os.path.exists(abs_local_file_path):
            # print("waiting for file creation.................")
            time.sleep(0.05) # wait until file is at least created
        time.sleep(0.05) # let the write get a slight head start before any reading

        all_cells = self.get_all_cell_text_from_latex_file(abs_local_file_path)

        # clean up self.local_latex_filename after writing and reading it
        if os.path.exists(self.local_latex_filename):
            os.remove(self.local_latex_filename)
        return all_cells

    def get_all_cell_text_from_latex_file(self, filename):
        """Read all the special cell text from the Latex file "filename."
        Return a list of Cell class instances, where each instance for a cell
        is a list of lines (and some additional data) corresponding to the
        lines of a cell in the document (in the order that they appear in the
        document).

        To update the data and then call this function, use getAllCellText() with
        flag useLatexExport=True.
        """
        latex_file = TerminatedFile(filename, r"\end{document}",
                                    err_msg_location="get_all_cell_text_from_latex_file")
        cell_list = []
        inside_cell = False
        while True:
            line = latex_file.readline()
            if line == "":
                break
            # search lines starting with \begin{lyxNotebookCell, \end{lyxNotebookCell,
            # or a cookie at the start of a cell line or anywhere in an ordinary line
            if line.find(r"\begin{lyxNotebookCell") == 0 and line.strip()[-1] == "}":
                inside_cell = True
                cell_list.append(Cell()) # create a new cell
                cell_list[-1].begin_line = line # begin{} may have meaningful args later
                cell_list[-1].begin_line_number = latex_file.number
                # did we find a cookie earlier that needs to be recorded with new cell?
            elif line.find(r"\end{lyxNotebookCell") == 0 and line.strip()[-1] == "}":
                cell_list[-1].end_line = line # include the end{} markup, too
                cell_list[-1].end_line_number = latex_file.number
                inside_cell = False
            elif inside_cell:
                # TODO: detect multiple cookies inside a cell (here and below routine)
                # Can delete any multiples with or without raising error message.
                # See the TODO in below routine (which is now used instead of this one
                # by default).
                if line.find(self.magic_cookie) == 0: # cell cookies must begin lines, too
                    cell_list[-1].has_cookie_inside = True
                    line = line.replace(self.magic_cookie, "", 1) # replace one occurence
                cell_list[-1].append(line) # got a line in the cell, append it
            else: # got an ordinary text line
                if line.find(self.magic_cookie) != -1: # found cookie anywhere on line
                    cookie_not_in_cell_line_num = latex_file.number
        return cell_list

    def export_latex_to_lyx_temp_dir(self):
        """Update the Lyx temporary directory's version of exported Latex (for
        the current buffer).  Note that this is different from just exporting to
        Latex.  This is just a wrapper for an LFUN, and should not usually be
        called by higher-level routines.  Higher-level routines should use
        getAllCellText(), which updates the save file and gets the cell data from
        it."""
        # return self.process_lfun("buffer-update-dvi") # dvi version doesn't work
        # doing below twice gives "command disabled" on second try, first returns
        # empty data string in INFO message
        self.process_lfun("buffer-update", "ps")

    def export_latex_to_file(self, filename):
        """Exports plain Latex to filename.  Note that the LFUN command seems to
        prefer absolute pathnames, especially when Lyx notebook is running
        without a terminal (for some reason)."""
        self.process_lfun("buffer-export-custom", "latex cat $$FName >" + filename)

    #
    # Dead code below, but parts might still be usable.
    #

    def get_most_recent_temp_dir_latex_filename(self):
        """Returns the filename of the most recently updated "export to latex" in
        the Lyx temp directory.  The ls command used assumes the file is the most
        recent one in the Lyx temp dir which matches: lyx*/*/*.tex"""
        # This function is now UNUSED; it was mainly for server-goto-file-row
        # experiments which didn't turn out well.  If needed it could be made more
        # portable in a way similar to the insertMostRecentGraphicsFile code.

        # BROKEN, for example, retData is undefined.

        # (Note that the last ls option is the number 1, not the letter l.)
        ls_cmd = "ls -ct1 "+self.lyx_temporary_directory+"/lyx*/*/"+retData[1][:-4]+".tex"
        if os.system(ls_cmd+" >/dev/null"):
            print("Failed to find exported Latex file.")
            return []
        f = os.popen(ls_cmd)
        most_recent = f.readline().strip() # get first listed, strip off whitespace (\n)
        return most_recent


