# -*- coding: utf-8 -*-
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
http://wiki.lyx.org/sourcedoc/svn/namespacelyx.html#5ae63e8160e98b54ad28f142ed40c202
For similar technical notes, with raw newlines explicitly specified in the docs
where they are required (e.g. search and replace), see
http://www.koders.com/cpp/fidB982EF8F5299023FC858C1BB857347440F3A5302.aspx?s=vector

"""

# TODO it is probably doable to delete all magic cookies inside cells
# using lfuns.  First, detect extraneous ones.  Then, 1) goto beginning
# and 2) do word-find-forward <magicCookie> 3) test if inside a cell
# 4) if so, do char-delete-forward which should delete the full highlighted
# (char-delete-backward does the same).  5) repeat the whole process until
# it works, unless there is some way to detect failure in word-find-forward
# in which case you can just do that part again until it fails.

from __future__ import print_function, division
import sys
import os
import time
import datetime
import getpass
import random
import string # just for generating random filenames
import easygui_096 as eg
import lyxNotebook_user_settings

# This file is repeatedly written temporarily to current dir, then deleted.
tmp_saved_lyx_file_name = "tmp_save_file_lyx_notebook_xxxxx.lyxnotebook"

class Cell(list):

    """Simple container class derived from a list.  It is meant to hold lines
    of text corresponding to the contents of a cell.  The line numbers are
    relative to Latex files (when the cell text is extracted from such files)."""
    # TODO: maybe go back to list as internal, using composition.  Inheriting
    # from list isn't a great idea.  General list operations return lists,
    # not Cell subclasses.

    def __init__(self):
        # TODO call __init__ method from base class list, or don't inherit from list
        self.hasCookieInside = False  # is there a cookie inside this cell?
        self.cookieLineBefore = -1    # cookie between cell and prev? line number if so
        self.cookieLineAfter = -1     # cookie between cell and next? line number if so
        # self.lines = []  # now the base list class contains the lines
        self.beginLineNumber = -1 # the line number where the cell begins
        self.beginLine = ""       # the text of the begin line (i.e., the Latex \begin)
        self.endLineNumber = -1   # the line number where the cell ends
        self.endLine = ""         # the text of the end line (i.e., the Latex \end)
        self.cookieLine = -1      # the line where the last cookie in file is found
        self.evaluationOutput = None # list of lines resulting from code evaluation

    def getCellType(self):
        """Note this depends on the naming convention in the .module files.
        Returns an ordered pair (<basictype>,<language>).  For example,
        ("Standard", "Python")."""
        if self.beginLine == -1: return None
        if self.beginLine.find(r"\begin_inset Flex LyxNotebookCell") == 0: # from Lyx
            splitLine = self.beginLine.split(":")
            language = splitLine[-1].strip()
            basicType = splitLine[-2].strip()
        else: # from a Latex file, \begin{...
            beginPos = self.beginLine.find("{")+1
            endPos = self.beginLine.find("}")
            typeString = self.beginLine[beginPos:endPos]
            if typeString.find("lyxNotebookCellStandard") == 0:
                language = typeString[len("lyxNotebookCellStandard"):]
                basicType = "Standard"
            elif typeString.find("lyxNotebookCellInit") == 0:
                language = typeString[len("lyxNotebookCellInit"):]
                basicType = "Init"
            elif typeString.find("lyxNotebookCellOutput") == 0:
                language = typeString[len("lyxNotebookCellOutput"):]
                basicType = "Output"
            else:
                language = None
                basicType = None
        return (basicType, language)


class TerminatedFile(object):

    """A class to read lines from a file with a known termination line, which may
    not be finished writing by a writer process.  This is to deal with possible
    race conditions.  The EOF line "" will be returned only after the file
    terminator has been seen, otherwise it will try again after a short delay.
    Also provides a pushback buffer for lookahead.  The data field number is
    incremented on each line read up to EOF (and decremented on pushback).  The
    errLocation string is made part of any warning message; it should include the
    name of the routine where the class instance is declared."""

    def __init__(self, filename, terminationString, errLocation):
        self.fileIn = open(filename, "r")
        self.terminationString = terminationString
        self.errLocation = errLocation
        self.bufferLines = []
        self.foundTerminator = False
        self.number = 0

    def readline(self):
        while True:
            if len(self.bufferLines) != 0: line = self.bufferLines.pop()
            else: line = self.fileIn.readline()
            if line == "" and not self.foundTerminator:
                time.sleep(0.05)
                print("Warning: read process faster than write in " + self.errLocation)
                continue
            if line.rstrip() == self.terminationString: self.foundTerminator = True
            if line != "": self.number += 1
            return line

    def pushback(self, line):
        if line != "":
            if line.rstrip() == self.terminationString: self.foundTerminator = False
            self.bufferLines.append(line)
            self.number -= 1

    def close(self):
        self.fileIn.close()


def convertTextLineToLyxFileInsetFormat(textLine):
    """This utility function takes a single line of text as a string and returns
    a string corresponding to the Lyx file format of that line when it
    is inside a Lyx Notebook inset (i.e., in a Plain Layout block)."""
    result = "\\begin_layout Plain Layout\n"
    # replace all backslashes with \backslash on a separate line
    textLineNew = textLine.replace("\\", "\n\\backslash\n")
    # split long lines at 80 chars (not quite right, compare later)
    # just try to make the diffs almost match and be a valid Lyx file
    splitLineNew = textLineNew.splitlines() # don't keep ends
    wrappedLineNew = []
    for line in splitLineNew:
        breakLen = 80
        while True:
            if len(line) <= breakLen: # at most breakLen chars in line
                wrappedLineNew.append(line + "\n")
                break
            else: # more than breakLen chars len(line) > breakLen
                def calcBreakPoint(breakStr, minVal):
                    place = line[:breakLen].rfind(breakStr)
                    if place > minVal: return place
                    return breakLen
                breakPoint = min(calcBreakPoint("\t", 70),
                                 calcBreakPoint(" ", 70),
                                 calcBreakPoint(".\t", 10),
                                 calcBreakPoint(". ", 10))
                wrappedLineNew.append(line[:breakPoint] + "\n")
                line = line[breakPoint:]
    wrappedLineNew.append("\\end_layout\n\n")
    result += "".join(wrappedLineNew)
    return result


class InteractWithLyxCells(object):

    """The main class for handling interactions with a running Lyx process
    via the Lyx server.  Also handles writing and reading data from files in
    the user's home Lyx directory."""

    def __init__(self, clientName):
        """Initialize; clientName is arbitrary but should be a unique identifier."""

        self.clientName = clientName

        # make userName part of temp file to avoid conflicts: different users, same dir
        userName = getpass.getuser()
        self.localLatexFilename = "zzzTmpTmp_"+userName+"_LyxNotebook_TmpTmp.tex"

        lyxServerPipe = lyxNotebook_user_settings.lyxServerPipe
        self.lyxServerPipe = os.path.abspath(os.path.expanduser(lyxServerPipe))
        lyxTemporaryDirectory = lyxNotebook_user_settings.lyxTemporaryDirectory
        self.lyxTemporaryDirectory = os.path.abspath(
            os.path.expanduser(lyxTemporaryDirectory))

        self.lyxServerReadEventBuffer = []  # buffer for the events read from the pipe

        # a temp file is written in the Lyx temp dir
        # to avoid conflicts it uses clientname and has eight random characters added
        # (this could be improved a bit, check exists, but good enough for now)
        rndAlphanum8 = \
            ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(8))
        self.tempCellWriteFile = self.lyxTemporaryDirectory + \
            "/zLyxNotebookCellTmp_" + clientName + userName + rndAlphanum8 + ".txt"

        self.lyxServerPipeInFilename = self.lyxServerPipe + ".in"
        self.lyxServerPipeOutFilename = self.lyxServerPipe + ".out"

        # check that named pipes exist
        print()
        if not self.lyxNamedPipesExist():
            print("No LyX process running (nonexistent lyxpipe file).")
            print("Start up LyX and try again.  If LyX is running, check the")
            print("lyxpipe settings in LyX and in lyxNotebook_user_settings.py.")
            print()
            time.sleep(4) # pause a few seconds so xterm window displays are readable
            sys.exit(1)

        # these single file opens seem to work here, rather than repeated in processLfun
        self.lyxServerPipeIn = os.open(self.lyxServerPipeInFilename, os.O_WRONLY)
        self.lyxServerPipeOut = \
            os.open(self.lyxServerPipeOutFilename, os.O_RDONLY | os.O_NONBLOCK)

        # empty out and ignore any existing replies or notify-events (for Lyx
        # Notebook commands) which are in the lyxServerPipeOut
        while True:
            if self.getServerEvent() is None: break

        # Magic cookie initializations.

        # Magic cookies CANNOT contain ";" or the command-sequence LFUN will fail,
        # and the program has only been tested with alphanumeric cookies.
        self.magicCookie = lyxNotebook_user_settings.magicCookieString

        # not all of these LFUN strings are currently used, but they may be at some time
        self.delCookieForwardString = ""
        self.delCookieBackwardString = ""
        self.backCookieString = ""
        for i in range(0, len(self.magicCookie)):
            self.delCookieForwardString += "char-delete-forward;"
            self.delCookieBackwardString += "char-delete-backward;"
            self.backCookieString += "char-left;"

        return # end of __init__

    def setMagicCookie(self, string):
        """Set the magic cookie value.  A convenience function, instead of just
        using the magicCookie member variable.  Only alphanumeric cookies have
        been tested."""
        self.magicCookie = string

    def getMagicCookie(self):
        """Return the current value of the magic cookie."""
        return self.magicCookie

    #
    #
    # Routines for low-level communications with Lyx via the named pipes.
    #
    #

    def lyxNamedPipesExist(self):
        """Do the special Lyx named pipe files exist?  True or False."""
        return (os.path.exists(self.lyxServerPipeInFilename)
                and os.path.exists(self.lyxServerPipeOutFilename))

    def processLfun(self, lfunName, argument="", warnERROR=True, warnNotINFO=True):
        """Process the Lyx LFUN in the currently running Lyx via the server."""
        # TODO: modify to return whole parsed reply list... only a few funs all in
        # this file use the return value, and they can just bracket the third component.
        # Then we get more info on ERROR returns, etc.

        # WARNING, Unix pipes *cannot* be treated like ordinary files in Python.
        # We need to treat them like low-level OS objects and use os.open, os.read
        # and os.write on them.  We must also specify non-blocking reads.

        # first convert the command to server's protocol, then send it
        serverProtocolString = "LYXCMD:" + self.clientName + ":" \
                                         + lfunName + ":" + argument + "\n"
        serverProtocolString = serverProtocolString.encode("utf-8") # for Python3
        while True:
            try:
                os.write(self.lyxServerPipeIn, serverProtocolString)
                break
            except: # TODO what specific exceptions?
                #time.sleep(0.01)
                time.sleep(0.001)

        # now read the reply from the output pipe, and handle ERROR cases
        while True: # later we may want to continue on errors below, so loop
            parsedList = self.waitForServerEvent(notify=False) # note NOTIFY ignored
            if warnERROR and parsedList[0] == "ERROR":
                print("Warning: Ignoring an ERROR message in processLfun(),",
                      "the parsed message list is:\n", parsedList)
            elif warnNotINFO and parsedList[0] != "INFO":
                print("Warning: Got a non-INFO unknown reply from LyX Server" +
                      " in processLfun.  Ignoring it.")
            break
        #print("debug end of processLfun:", parsedList)
        return parsedList[3].rstrip("\n")

    def getServerEvent(self, info=True, error=True, notify=True):
        """Reads a single event from the Lyx Server.  If no event is there to
        be read it returns None.  If any flag is False then that type of event
        is completely ignored.  Returns a parsed list with the strings of the
        Lyx server events (but not the colon separator, and keeping the final
        newline on the last element in the list).

        This routine is repeated in a polling loop to wait for an event in the
        routine self.waitForServerEvent().  It can also be used outside a wait
        loop, for example, calling it with all cell types False will empty
        out all events, buffered and pending, and return None.

        If a NOTIFY event from the server is ignored it nonetheless sets the
        flag self.ignoredServerNotifyEvent to True.  This flag can be initialized
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
            if len(self.lyxServerReadEventBuffer) == 0: # could be if
                if not self.lyxNamedPipesExist():
                    print("LyX server named pipes no longer exist; LyX must have closed.")
                    print("Exiting the LyX Notebook program.")
                    time.sleep(3) # for xterm displays
                    sys.exit(0)
                try:
                    rawReply = os.read(self.lyxServerPipeOut, 1000)
                except:
                    return None
                # convert returned byte array to unicode string
                rawReply = rawReply.decode("utf-8") # for Python3 compatibility

                # check for multiple commands, assume they split on lines...
                allEvents = rawReply.splitlines()
                for event in allEvents:
                    # parse the event
                    parsedList = event.split(":", 3)
                    self.lyxServerReadEventBuffer.append(parsedList)

            # now we know buffer is not empty, so pop an event off and analyze it
            parsedList = self.lyxServerReadEventBuffer.pop()

            # check the type of event and compare with flags...
            if parsedList[0] == "NOTIFY":
                if not notify:
                    self.ignoredServerNotifyEvent = True
                    #print("debug =============================== IGNORED NOTIFY")
                    continue
                else: break
            elif parsedList[0] == "ERROR":
                if not error: continue
                else: break
            elif parsedList[0] == "INFO":
                if not info: continue
                else: break
            else: # ignore unknown, but print warning
                print("Warning: getServerEvent() read an unknown message type" +
                      " from LyX Server:", parsedList)
        return parsedList

    def waitForServerEvent(self, info=True, error=True, notify=True):
        """Go into a loop, waiting for an event from the Lyx process.  If the
        flag for any type of event is False then that type of event is ignored.
        """
        while True:
            parsedList = self.getServerEvent(info=info, error=error, notify=notify)
            if parsedList is None:
                try:
                    #time.sleep(0.5) # polling, half-second response
                    time.sleep(0.25) # polling, quarter second response
                    # don't count the retries, may be polling for hours or even days
                except KeyboardInterrupt:
                    print("\nLyX Notebook exiting after keyboard interrupt.  Bye.")
                    sys.exit(0)
            else: break
        return parsedList

    def waitForServerNotify(self):
        """This routine waits for a NOTIFY event, ignoring all others.  When it
        gets one, it returns only the actual keyboard key that was pressed, with
        the trailing newline stripped.  This is called from higher-level routines
        to wait for a Lyx command-key sent by server-notify (they then to "wake up"
        and perform the action).  Thus all command-keys in Lyx for this application
        are bound to the LFUN "server-notify" (usually in a .bind file in the
        local .lyx directory)."""
        parsedList = self.waitForServerEvent(info=False, error=False)
        # The second and last component of NOTIFY has the key:
        #   NOTIFY:<keyPressed>
        keyPressed = parsedList[1].rstrip("\n")
        return keyPressed

    #
    #
    # Higher-level commands to perform simple tasks in Lyx.  Some just wrap LFUNs.
    #
    #

    def serverGetFilename(self):
        """Return the pathname of the file being edited in the current buffer."""
        return self.processLfun("server-get-filename")

    def serverGetLayout(self):
        """Get the layout for the current cursor position."""
        return self.processLfun("server-get-layout")

    def showMessage(self, string):
        """Print the message in the status bar in Lyx."""
        #self.processLfun("message", string)
        # BUG in Lyx 2.0.3.  Message alone doesn't show, but does as command-sequence!
        self.processLfun("command-sequence", "message "+string)

    def charLeft(self):
        self.processLfun("char-left") # don't bother returning value

    def charRight(self):
        self.processLfun("char-right") # don't bother returning value

    def insideCell(self):
        """Are we inside a cell of the type associated with this class?  Only
        partially accurate, since it can only check the layout type and cannot
        distinguish between listings insets and custom wrapped listings insets
        (or anything else that returns "Plain Layout" from LFUN server-get-layout).
        That is, a True result is a necessary but not a sufficient condition."""
        return self.serverGetLayout() == "Plain Layout"

    def insideMathInset(self):
        """Test if we are inside a math inset.  Tries a math-size LFUN to see if
        it fails."""
        # TODO:  run processLfun ignoring ERROR messages
        testString = self.processLfun("math-size")
        print("debug testString is", testString)
        return not testString.strip() == "Command disabled"

    def atCellBegin(self, assertInsideCell=False):
        """Are we at the beginning of the cell, still inside it?  The
        "assertInsideCell" optional argument allows avoiding a Lyx server
        operation (expensive) when that condition is already known to be true.
        All "assert" arguments are for efficiency only, and can always be made
        False (turn off optimization) if bugs occur."""
        if not assertInsideCell:
            if not self.insideCell(): return False
        retval = False
        self.charLeft()
        if not self.insideCell(): retval = True
        self.charRight() # undo the test
        return retval

    def atCellEnd(self, assertInsideCell=False):
        """Are we at the end of the cell, still inside it?  The
        "assertInsideCell" optional argument allows avoiding a Lyx server
        operation (expensive) when that condition is already known to be true.
        All "assert" arguments are for efficiency only, and can always be made
        False (turn off optimization) if bugs occur."""
        if not assertInsideCell:
            if not self.insideCell(): return False
        retval = False
        self.charRight()
        if not self.insideCell(): retval = True
        self.charLeft() # undo the test
        return retval

    def insideEmptyCell(self, assertInsideCell=False):
        return self.atCellBegin(assertInsideCell) and self.atCellEnd(assertInsideCell)

    def gotoCellBegin(self, assertInsideCell=False):
        """Goes to beginning of current cell.  The LFUN inset-begin works
        differently when it is already at the beginning -- it goes to the outer
        inset level.  This is modified to always stay inside (idempotent).
        Note that inset-end works similarly at the end, so can't just use that.
        The "assertInsideCell" optional argument can speed things up just a little."""
        # One alternative to consider to get gotoCellEnd is escape and then as many
        # char-left (one or two) as are required to get back insideCell, but may
        # need double escape if something highlighted...
        if not assertInsideCell:
            if not self.insideCell(): return
        if True: # faster implementation than "else", still testing, though
            self.processLfun("line-begin")
            if not self.atCellBegin(assertInsideCell=True):
                self.processLfun("inset-begin")
            return
        else: # this else never executes, previous implementation, more operations
            if self.atCellBegin(assertInsideCell=True):
                if self.atCellEnd(assertInsideCell=True):
                    return # inside an empty cell, so at beginning
                self.charRight() # set to not already at begin, for LFUN inset-begin
            self.processLfun("inset-begin")
            return

    def selfInsert(self, string):
        """Inserts string at the cursor point, but cannot handle embedded newlines."""
        if string == "": return "empty string nothing done"
        return self.processLfun("self-insert", string)

    def selfInsertLine(self, string):
        """Adds newline after the string, but doesn't work in listings."""
        self.selfInsert(string)
        return self.processLfun("newline-insert")

    def exportLatexToLyxTempDir(self):
        """Update the Lyx temporary directory's version of exported Latex (for
        the current buffer).  Note that this is different from just exporting to
        Latex.  This is just a wrapper for an LFUN, and should not usually be
        called by higher-level routines.  Higher-level routines should use
        getAllCellText(), which updates the save file and gets the cell data from
        it."""
        # return self.processLfun("buffer-update-dvi") # dvi version doesn't work
        # doing below twice gives "command disabled" on second try, first returns
        # empty data string in INFO message
        self.processLfun("buffer-update", "ps")
        return

    def exportLatexToFile(self, filename):
        """Exports plain Latex to filename.  Note that the LFUN command seems to
        prefer absolute pathnames, especially when Lyx notebook is running
        without a terminal (for some reason)."""
        self.processLfun("buffer-export-custom", "latex cat $$FName >" + filename)
        return

    def openAllCells(self, init=True, standard=True, output=True):
        """Open all cells of the type associated with this class.  Only implemented
        for all cells or a single type of cell being selected by flags (but could
        be extended)."""
        if init and standard and output:
            cellType = "Flex:LyxNotebookCell"
        elif init:
            cellType = "Flex:LyxNotebookCell:Init"
        elif standard:
            cellType = "Flex:LyxNotebookCell:Standard"
        elif output:
            cellType = "Flex:LyxNotebookCell:Output"
        self.processLfun("inset-forall", cellType+" inset-toggle open")
        return

    def closeAllCellsButCurrent(self, init=True, standard=True, output=True):
        """Open all cells of the type associated with this class.  Only implemented
        for all cells or a single type of cell."""
        # could be consolidated with openAllCells() with an optional argument
        if init and standard and output:
            cellType = "Flex:LyxNotebookCell"
        elif init:
            cellType = "Flex:LyxNotebookCell:Init"
        elif standard:
            cellType = "Flex:LyxNotebookCell:Standard"
        elif output:
            cellType = "Flex:LyxNotebookCell:Output"
        self.processLfun("inset-forall", cellType+" inset-toggle close")
        return

    def gotoBufferBegin(self):
        """Goto the beginning of the document in the current buffer."""
        return self.processLfun("buffer-begin")

    def gotoBufferEnd(self):
        """Goto the end of the document in the current buffer."""
        return self.processLfun("buffer-end")

    def insertMagicCookieInsideCurrent(self, onCurrentLine=False,
                                       assertInsideCell=False):
        """Inserts the magic cookie into the cell.  By default the position is at
        the top left of the inset.  Using the option to put it on the current line
        saves a few operations, since we don't have to find the inset beginning,
        but the same option must also be set in cookie delete and the current line
        cannot change in the meantime (or someother assertion like undo or
        cursor-end must be made on delete)."""
        if not assertInsideCell:
            if not self.insideCell(): return # not even in a cell, do nothing
        if onCurrentLine:
            self.processLfun("line-begin")
        else:
            self.gotoCellBegin(assertInsideCell=True)
        return self.processLfun("self-insert", self.magicCookie)

    def deleteMagicCookieInsideCurrent(self, assertInsideCell=False,
                                 assertCursorAtCookieEnd=False, onCurrentLine=False):
        """Assumes the cookie is present as the first chars of the special inset type
        (unless onCurrentLine is True, in which case the beginning of the current
        line is assumed).  Assertion args can be used for efficiency if the conditions
        are known to hold.  For undo to be sufficient, no intermediate actions can
        have been taken which count as changes to undo."""
        if assertCursorAtCookieEnd:
            return self.processLfun("word-delete-backward")
        if not assertInsideCell:
            if not self.insideCell(): return # we're not even in a cell
        if onCurrentLine:
            self.processLfun("line-begin")
        else:
            self.gotoCellBegin(assertInsideCell=True)
        self.processLfun("command-sequence", self.delCookieForwardString)
        return

    def insertMagicCookieInsideForall(self, cellType="Flex:LyxNotebookCell"):
        """Inserts the cookie inside all the selected insets, as beginning chars."""
        # to insert cookies before cells, not inside, just remove the char-right
        return self.processLfun("inset-forall",
                 cellType+" command-sequence char-right ; self-insert "+self.magicCookie)

    def deleteMagicCookieInsideForall(self, cellType="Flex:LyxNotebookCell"):
        """Deletes the magic cookie from all insets, assumed inside at beginning."""
        #delString = ""
        #for i in range(0,len(self.magicCookie)): delString += "char-delete-forward;"
        # TODO would it be possible to just globally delete the cookie from the
        # whole file?  Could do that before any operations and then afterwards to
        # avoid errors due to cookies left after errors.  LyX 2.0 now has
        # advanced search; look into that and any useful lfuns.
        return self.processLfun("inset-forall",
                   cellType+" command-sequence char-right;"+self.delCookieForwardString)

    def searchNextCookie(self):
        """Search for (goto) the next cookie in the buffer."""
        self.processLfun("word-find-forward", self.magicCookie)

    def searchPrevCookie(self):
        """Search for (goto) the previous cookie in the buffer."""
        self.processLfun("word-find-backward", self.magicCookie)

    #
    #
    # Goto operations in Lyx
    #
    #

    def gotoNextCell(self, standard=True, init=True, output=True, reverse=False):
        """Go to the next cell (of the type selected by the flags).  Currently
        only works with open cells, so the command-loop opens them all before
        calling this function.  The boolean arguments allow the type of cells
        to be chosen.

        Uses Lyx LFUNs with a magic cookie rather than file operations
        and server-goto-file-row."""

        cellTypeList = []
        if standard:
            cellTypeList.append("Flex:LyxNotebookCell:Standard")
        if init:
            cellTypeList.append("Flex:LyxNotebookCell:Init")
        if output:
            cellTypeList.append("Flex:LyxNotebookCell:Output")
        if len(cellTypeList) == 3:
            cellTypeList = ["Flex:LyxNotebookCell"]

        for cellType in cellTypeList:
            self.insertMagicCookieInsideForall(cellType=cellType)

        if reverse: # reverse search
            if not self.insideCell(): self.searchPrevCookie()
            else:
                self.charRight() # char right so always find current cookie first
                self.searchPrevCookie()
                self.searchPrevCookie()
        else: # forward search
            #self.charRight() # in case at the beginning of inset, won't hurt elsewhere
            #self.searchNextCookie()
            # combine the two lines above into one server call for a bit more efficiency
            self.processLfun("command-sequence",
                             "char-right;word-find-forward "+self.magicCookie)
        for cellType in cellTypeList:
            self.deleteMagicCookieInsideForall(cellType=cellType)

        # Note on goToNextCell() for mixed open and closed cells.
        # We might want to have the next cell opened if it is closed, and no
        # others.... not easy to implement, though, so currently all are opened.
        # Forward goto as above ends up inside cell if open, but after the cell
        # by the length of the cookie if the cell is closed.
        # (Cookies don't go inside when forall insert is called and they
        # are closed, they go after.)  Deleting cookie still works OK but cursor is
        # left after the cell by len(magicCookie) spaces.
        # A first try below, but this fails for a closed cell immediately followed by
        # and open cell (and maybe others, and Prev not implemented).  Be sure to
        # also comment out the command-loop "global open" to test...
        #if not self.insideCell():
        #   self.processLfun("command-sequence",
        #         self.backCookieString+"char-left;inset-toggle open;char-right")

        self.gotoCellBegin() # this also checks for insideCell(), last may be outside
        return

    def gotoPrevCell(self, standard=True, init=True, output=True):
        """Reverse of gotoNextCell."""
        self.gotoNextCell(standard=standard, init=init, output=output,
                          reverse=True)

    def serverGotoFileRow(self, filename, linenum):
        r""" The line number must refer to a line in the exported Latex file in
        the Lyx temporary directory -- update if necessary using
        exportLatexToLyxTempDir().  method).  Note the numbered line must refer
        to a line of ordinary text or the line of a \begin statement for a cell
        or listing, not a line within a cell or listing environment.  Not used
        except in experimental gotoNextCell2 routine."""
        return self.processLfun("server-goto-file-row",
                                filename + " " + str(linenum))

    def gotoNextCell2(self, reverse=False):
        """An alternate implementation, using server-goto-file-row, not cookies.
        For now just a demo of how to do things that way.  The routines to
        write text to the cells could be done similarly.

        This routine once worked somewhat, but has not been kept updated.
        At the least it would have to be modified to use the Lyx temp directory
        latex export (which the main program no longer uses) since otherwise
        server-goto-file-row doesn't work.

        This code is kept as a reminder of how to use server-goto-file row.  It
        is not used because server-goto-file-row is not especially accurate.  It
        seems to almost always end up before the target cell, though, so we can
        "walk" forward the rest of the way with charRight().  Slow, and using a
        search on a global cookie insert would just be the standard
        implementation above.

        Even assuming the walking version, the serverGotoFileRow operation fails
        when between two empty cells are on the same line, and in some other
        cases.  Note that we still need to know where we are in Lyx, which
        currently seems to require a cookie (given the available LFUNs).  But
        deleting the cookie may also shift the text and make some line numbers
        invalid... maybe insert, say, a cookie in a comment and assume three file
        lines?

        In summary, this method does not seem as promising as the current method
        using inset-forall of cookies and then search.  At the least it would
        need some work."""

        #layout = self.getServerLayout() # later maybe check layout, Plain or Standard
        self.processLfun("command-sequence", "escape;escape;escape") # escape any insets

        # insert cookie at cursor point, note that this cookie goes into regular text
        self.processLfun("self-insert", self.magicCookie)

        # save the Latex and get the filename
        dirInfo = self.getUpdatedLyxDirectoryData()

        # Why not just do a search on the cookie in the first place,
        # from beginning of file or known earlier point?  Because we can't insert a
        # cookie in Lyx if we don't know where the cell is in Lyx!  We only know
        # some previous point, which may not even be in a cell.  We can only do
        # a global cookie insert and find forward or backward from there.  That is
        # what the ordinary version of this function does.  There seems to be no
        # real advantage to the serverGotoFileRow version without some new LFUNs
        # (actual or faked with other LFUNs).

        # remove cookie
        # we'd like to remove it later, but we will lose the positioning information
        # if we do it after the serverGoToFileRow...
        #self.processLfun("command-sequence", self.delCookieBackwardString)
        self.processLfun("undo") # only need undo here, update doesn't count as change

        # now read the Latex data for all the cells
        allCells = self.getAllCellTextFromLatex(dirInfo[2])
        # look at the cookieLineBefore and cookieLineAfter numbers to choose cell
        lineToGoto = -1
        for cell in allCells:
            if reverse: cookieLineNum = cell.cookieLineAfter
            else: cookieLineNum = cell.cookieLineBefore
            if cookieLineNum >= 0:
                lineToGoto = cell.beginLineNumber
                break
        if lineToGoto < 0:
            return # no cells to go to, do nothing
        self.serverGotoFileRow(dirInfo[2], lineToGoto)
        while not self.insideCell(): self.charRight() # walk to inside the next cell
        return

    #
    #
    # Operations to get and replace text in cells
    #
    #

    def getAllCellText(self, useLatexExport=False):
        """Returns a list of Cell data structures containing the text for each
        cell in the current buffer.  Always updates the file before reading it.
        It can read either from a locally exported .tex Latex file (with
        useLatexExport=True) or from a Lyx-format file saved temporarily to
        the current directory.  The Lyx-format version is currently preferred,
        and the older Latex version may now need minor fixes."""

        # Note getUpdatedLyxDirectoryData changes current dir to buffer's dir.
        (bufferDirName,
         bufferFileName,
         autoSaveFileName,
         fullPath) = self.getUpdatedLyxDirectoryData()

        if useLatexExport:
            # Export to local Latex file, and wait only briefly
            # TODO can use fullPath now instead of re-join
            absLocalFilePath = os.path.join(bufferDirName, self.localLatexFilename)
            if os.path.exists(absLocalFilePath): os.remove(absLocalFilePath)
            self.exportLatexToFile(absLocalFilePath)
            while not os.path.exists(absLocalFilePath):
                # print("waiting for file creation.................")
                time.sleep(0.05) # wait until file is at least created
            time.sleep(0.05) # let the write get a slight head start before any reading

            allCells = self.getAllCellTextFromLatex(absLocalFilePath)

            # clean up self.localLatexFilename after writing and reading it
            if os.path.exists(self.localLatexFilename):
                os.remove(self.localLatexFilename)
        else:
            # Export temporarily to a local file.
            full_tmp_name = os.path.join(bufferDirName, tmp_saved_lyx_file_name)
            self.processLfun("buffer-export-custom",
                             "lyx mv $$FName " + full_tmp_name, warnERROR=True)
            time.sleep(0.05) # let write get a slight head start before any reading
            allCells = self.getAllCellTextFromLyxFile(full_tmp_name)
            if os.path.exists(tmp_saved_lyx_file_name): os.remove(tmp_saved_lyx_file_name)
            """
            # old below, delete soon
            if autoSaveFileName != "": # there is an auto-save file
                time.sleep(0.05) # let write get a slight head start before any reading
                allCells = self.getAllCellTextFromLyxFile(autoSaveFileName)
            else: # no auto-save file, assume buffer unchanged but try a write anyway
                self.processLfun("buffer-write", warnERROR=False)
                time.sleep(0.05) # let write get a slight head start before any reading
                allCells = self.getAllCellTextFromLyxFile(bufferFileName)
            """
        return allCells

    def getAllCellTextFromLatex(self, filename):
        """Read all the special cell text from the Latex file "filename."
        Return a list of Cell class instances, where each instance for a cell
        is a list of lines (and some additional data) corresponding to the
        lines of a cell in the document (in the order that they appear in the
        document).

        To update the data and then call this function, use getAllCellText() with
        flag useLatexExport=True.
        """
        latexFile = TerminatedFile(filename, r"\end{document}",
                                   "getAllCellTextFromLatex")
        cellList = []
        insideCell = False
        setNextCellCookieLineBefore = -1
        while True:
            line = latexFile.readline()
            if line == "": break
            # search lines starting with \begin{lyxNotebookCell, \end{lyxNotebookCell,
            # or a cookie at the start of a cell line or anywhere in an ordinary line
            if line.find(r"\begin{lyxNotebookCell") == 0 and line.strip()[-1] == "}":
                insideCell = True
                cellList.append(Cell()) # create a new cell
                cellList[-1].beginLine = line # begin{} may have meaningful args later
                cellList[-1].beginLineNumber = latexFile.number
                # did we find a cookie earlier that needs to be recorded with new cell?
                if setNextCellCookieLineBefore >= 0:
                    cellList[-1].cookieLineBefore = setNextCellCookieLineBefore
                    setNextCellCookieLineBefore = -1
            elif line.find(r"\end{lyxNotebookCell") == 0 and line.strip()[-1] == "}":
                cellList[-1].endLine = line # include the end{} markup, too
                cellList[-1].endLineNumber = latexFile.number
                insideCell = False
            elif insideCell:
                # TODO: detect multiple cookies inside a cell (here and below routine)
                # Can delete any multiples with or without raising error message.
                # See the TODO in below routine (which is now used instead of this one
                # by default).
                if line.find(self.magicCookie) == 0: # cell cookies must begin lines, too
                    cellList[-1].hasCookieInside = True
                    line = line.replace(self.magicCookie, "", 1) # replace one occurence
                cellList[-1].append(line) # got a line in the cell, append it
            else: # got an ordinary text line
                if line.find(self.magicCookie) != -1: # found cookie anywhere on line
                    if len(cellList) > 0: cellList[-1].cookieLineAfter = latexFile.number
                    setNextCellCookieLineBefore = latexFile.number
        return cellList

    def getAllCellTextFromLyxFile(self, filename):
        """Read all the cell text from the Lyx file "filename."  Return a
        list of Cell class instances, where each cell is a list of lines (and
        some additional data) corresponding to the lines of a code cell in the
        document (in the order that they appear in the document).  All cell types
        are included.

        To save the file and then get the most recent data from the .lyx save
        file, call getUpdatedCellText() with flag useLatexExport=False.
        """

        inFile = TerminatedFile(filename, r"\end_document",
                                "getAllCellTextFromLyxFile")
        cellList = []
        insideCell = False
        insideCellLayout = False
        setNextCellCookieLineBefore = -1
        while True:
            line = inFile.readline();
            if line == "": break
            # search lines starting with something like
            #    \begin_inset Flex LyxNotebookCell:Standard:PythonTwo
            # or a cookie at the start of a cell line or anywhere in an ordinary line
            elif line.find(r"\begin_inset Flex LyxNotebookCell:") == 0:
                insideCell = True
                insideCellLayout = False
                cellList.append(Cell()) # create a new cell
                cellList[-1].beginLine = line # begin{} may have meaningful args later
                cellList[-1].beginLineNumber = inFile.number
                # did we find a cookie earlier that needs to be recorded with new cell?
                if setNextCellCookieLineBefore >= 0:
                    cellList[-1].cookieLineBefore = setNextCellCookieLineBefore
                    setNextCellCookieLineBefore = -1
            elif insideCell and line.rstrip() == r"\end_inset":
                cellList[-1].endLine = line
                cellList[-1].endLineNumber = inFile.number
                insideCell = False
            elif (insideCell and not insideCellLayout
                  and line.rstrip() == r"\begin_layout Plain Layout"):
                insideCellLayout = True
            elif insideCellLayout: # actual line of cell text on several lines
                cellLineComponents = [line]
                while True:
                    nextLine = inFile.readline().rstrip("\n") # drop trailing \n
                    # translate some Lyx codes to ordinary text
                    if nextLine.rstrip() == r"\backslash": nextLine = "\\"
                    # append the translated text
                    cellLineComponents.append(nextLine)
                    if nextLine.rstrip() == r"\end_layout": break
                insideCellLayout = False
                line = "".join(cellLineComponents[1:-1]) + "\n" # components to one line
                # TODO: detect multiple cookies inside a cell (here and above routine)
                if line.find(self.magicCookie) == 0: # cell cookies must begin lines, too
                    cellList[-1].hasCookieInside = True
                    line = line.replace(self.magicCookie, "", 1) # replace one occurence
                cellList[-1].append(line) # got a line from the cell, append it
            else: # got an ordinary text line
                if line.find(self.magicCookie) != -1: # found cookie anywhere on line
                    if len(cellList) > 0: cellList[-1].cookieLineAfter = inFile.number # TODO see next line
                    setNextCellCookieLineBefore = inFile.number # TODO was = lineNumber, but undefined, make = inFile.number, but double check
        return cellList

    def replaceAllCellTextInLyxFile(self, fromFileName, toFileName, allCells,
                                    init=True, standard=True):
        """Given a .lyx file fromFile, write out another .lyx file which has the
        same text but in which all cells are replaced by the cells in allCells.
        Currently only the selected code cells are replaced, and the code cells
        are assumed to have already been evaluated with output in their
        evaluationOutput data fields.  The corresponding output cells are always
        replaced, and created if necessary, filled with the data in that field.
        """
        inFile = TerminatedFile(fromFileName, r"\end_document",
                                "replaceAllCellTextInLyxFile")
        outFile = open(toFileName, "w")
        currentCell = -1
        while True:
            line = inFile.readline()
            if line == "": break
            elif line.find(r"\begin_inset Flex LyxNotebookCell:") == 0:
                outFile.write(line) # start the new cell
                # find out what basic type of cell it is (Init, Standard, or Output)
                if line.find(r"\begin_inset Flex LyxNotebookCell:Init") == 0:
                    basicType = "Init"
                    if not init: continue # just echo whole cell unless selected
                elif line.find(r"\begin_inset Flex LyxNotebookCell:Standard") == 0:
                    basicType = "Standard"
                    if not standard: continue # just echo it unless selected
                else: # else must be an isolated output cell
                    continue # output cells right after code cells are handed at same time
                # find the corresponding Cell in allCells
                while True:
                    currentCell += 1
                    bType, insetSpec = allCells[currentCell].getCellType()
                    if bType == basicType: break
                # do an error check here, make sure insetSpec matches not just basicType
                if not (line.find(
                        r"\begin_inset Flex LyxNotebookCell:"+bType+":"+insetSpec) == 0):
                    print("Error in batch evaluation, cells do not match, exiting.")
                    time.sleep(4) # for xterm window displays
                    sys.exit(1)
                # echo back all cell-header stuff to outFile until a plain layout starts
                while True:
                    line = inFile.readline()
                    if line.rstrip() == r"\begin_layout Plain Layout": break
                    else: outFile.write(line)
                # now eat the old cell text up to the inset end, and ignore it
                while line.rstrip() != r"\end_inset":
                    # later may want to check for cookie inside old cell
                    line = inFile.readline()
                #
                # Write the new cell text (it may have been modified in processing).
                #
                for cellLine in allCells[currentCell]:
                    outFile.write(convertTextLineToLyxFileInsetFormat(cellLine))
                # now end the cell in outFile
                outFile.write("\\end_inset\n")
                #
                # Now look ahead for an output cell; eat it all and ignore it if found.
                #
                savedLines = []
                while True:
                    savedLines.insert(0, inFile.readline())
                    # save lines up to first non-empty, then break
                    if savedLines[0].rstrip() != "": break
                if savedLines[0].find(
                        r"\begin_inset Flex LyxNotebookCell:Output:"+insetSpec) == 0:
                    # got an output cell, eat it
                    while True:
                        if inFile.readline().rstrip() == r"\end_inset": break
                else:
                    # no output, pushback all saved lines
                    for line in savedLines: inFile.pushback(line)
                outFile.write("\n\n") # two blank lines between insets
                #
                # Ready to write a new output cell, in both cases.
                #
                outFile.write(
                    r"\begin_inset Flex LyxNotebookCell:Output:"+insetSpec+"\n")
                outFile.write("status open\n\n") # always create an open cell
                evalOutput = allCells[currentCell].evaluationOutput
                # if cell wasn't evaluated the set output to be empty
                if evalOutput is None: evalOutput = []
                for cellLine in evalOutput:
                    outFile.write(convertTextLineToLyxFileInsetFormat(cellLine))
                # finished, end the output cell inset
                outFile.write("\\end_inset\n") # 2 blanks pushed back from code cell end
            #
            # Got an ordinary Lyx file line.
            #
            else: # got an ordinary Lyx file line, so just echo it to output
                if line.find(self.magicCookie) != -1: # found cookie anywhere on line
                    pass # later may want to do something if cookie was found
                outFile.write(line)
        inFile.close()
        outFile.close()
        return

    def getUpdatedLyxDirectoryData(self, autoSaveUpdate=False):
        """
        This function returns a tuple of the form:
           (<currentBufferFileDirectory>,<currentBufferFilename>,
           <auto-saveFilename>, <currentBufferFullPath>)
        It tries to save an auto-save file (unless autoSaveUpdate is False), and
        returns "" for the auto-save file if the file still does not exist.  The
        current directory is always changed to <currentBufferFileDirectory>.
        """
        # get the ordinary pathname and directory name of the buffer file
        fullpath = self.serverGetFilename()
        dirname = os.path.dirname(fullpath)
        basename = os.path.basename(fullpath)

        # change directory (the document in the current buffer may change, new dir)
        os.chdir(dirname)

        # try a save to auto-save file, then check if one exists newer than basename
        # (latter check needed for initial files which haven't been changed)
        if autoSaveUpdate: self.processLfun("buffer-auto-save")
        autoSaveFilename = "#" + basename + "#"
        if not os.path.exists(autoSaveFilename): autoSaveFilename = ""
        elif (os.path.exists(basename)
              and os.stat(autoSaveFilename).st_mtime < os.stat(basename).st_mtime):
            print("Warning: auto-save file older than buffer file, not using it.")
            autoSaveFilename = ""

        # return the tuple
        retData = (dirname, basename, autoSaveFilename, fullpath)
        return retData

    def getMostRecentTempDirLatexFilename(self):
        """Returns the filename of the most recently updated "export to latex" in
        the Lyx temp directory.  The ls command used assumes the file is the most
        recent one in the Lyx temp dir which matches: lyx*/*/*.tex"""
        # This function is now UNUSED; it was mainly for server-goto-file-row
        # experiments which didn't turn out well.  If needed it could be made more
        # portable in a way similar to the insertMostRecentGraphicsFile code.
        # It is BROKEN, for example, retData is undefined.

        # (Note that the last ls option is the number 1, not the letter l.)
        lsCmd = "ls -ct1 "+self.lyxTemporaryDirectory+"/lyx*/*/"+retData[1][:-4]+".tex"
        if os.system(lsCmd+" >/dev/null"):
            print("Failed to find exported Latex file.")
            return []
        f = os.popen(lsCmd)
        mostRecent = f.readline().strip() # get first listed, strip off whitespace (\n)
        return mostRecent

    def getGlobalCellInfo(self, useLatexExport=False):
        """This routine returns a list
            (numInitCells, numStandardCells, numOutputCells)
        which is used in multiple-cell evaluations from inside Lyx.  Basically we
        need to know how many cells of each type to loop over using the cell-goto
        commands, and this function gets the data."""
        cellList = self.getAllCellText(useLatexExport=useLatexExport)
        numInitCells = 0
        numStandardCells = 0
        numOutputCells = 0
        for cell in cellList:
            basicType, language = cell.getCellType()
            if basicType == "Init": numInitCells += 1
            elif basicType == "Standard": numStandardCells += 1
            elif basicType == "Output": numOutputCells += 1
        return (numInitCells, numStandardCells, numOutputCells)

    def getCurrentCellText(self, useLatexExport=False):
        r"""Returns a Cell data structure containing the current text of the cell,
        as lines.  Returns None if the cursor is not currently inside a cell.
        The \begin and \end Latex markers (or Lyx markers) for the cell type are not
        included as lines of a Cell, but they are saved as additional fields.
        This currently works by putting a cookie in the current cell, updating the
        save/export, removing the cookie, and then reading all the cells in from
        that file and looking for which one has the cookie.  (This routine is
        nontrivial due to a lack of LFUNs to do it more directly.)"""

        # This routine is similar to getAllCellText() except the current cell has
        # to be singled out (identified with a cookie).
        if not self.insideCell(): return None # return None if not in a cell
        self.insertMagicCookieInsideCurrent(assertInsideCell=True,
                                            onCurrentLine=True)
        allCells = self.getAllCellText(useLatexExport=useLatexExport)
        self.deleteMagicCookieInsideCurrent(assertCursorAtCookieEnd=True)
        foundCookie = False
        for cell in allCells:
            if cell.hasCookieInside:
                if foundCookie:
                    err_msg = ("\n\nWARNING: multiple cells have cookies inside them."
                          "\nNot performing the operation.  Globally delete the"
                          "\ncookie string " + self.magicCookie + " from the"
                          " document and try again.\n")
                    print(err_msg, file=sys.stderr)
                    eg.msgbox(msg=err_msg, title="LyX Notebook", ok_button="OK")
                    return None
                foundCookie = True
                returnCell = cell
        # return Cell() # Was causing bugs in ordinary Listings cells, now return None.
        if foundCookie: return returnCell
        else: return None

    def replaceCurrentOutputCellText(self, lineList, createIfNecessary=True,
               gotoBeginAfter=False, assertInsideCell=False, insetSpecifier="Python"):
        """Replace the text of the output cell corresponding to the current Standard
        or Init cell.  The cell must immediately follow.  If it doesn't and
        createIfNecessary is True then one will be created/inserted.  The default
        is a Python cell; this can be changed by setting insetSpecifier to a value
        from one of the other interpreter specs."""

        if not assertInsideCell:
            if not self.insideCell(): return # not even in a cell

        # First we run a big command-sequence to do the following:
        # -- use inset-select-all and two escapes to leave the inset (first escape
        #    turns off any selections so second always exits the inset)
        # -- word-backward to goto before the inset, then try to open it in case it
        #    is closed (newly inserted cells are closed, inconvenient and causes probs
        #    problems at EOF) then word-forward to go back to after the inset
        # -- inset-toggle open to open any output cell which might be there (if
        #    there is one and it is closed we can't move inside it in next step)
        # -- go right one char (to prepare to test if an inset immediately follows).
        #
        # (For some reason in 2.0.3 the inset-select-all doesn't gives the nice blue
        # selection-highlighting feedback when called this way, so it is added
        # in the evaluateCell routine if text in code cells isn't replaced.)
        self.processLfun("command-sequence",
                         "inset-select-all;escape;escape;word-backward;inset-toggle open;word-forward;inset-toggle open;char-right")

        # At this point, if there is an inset afterward we are inside it.

        # first test if inside a math inset... still in development
        # TODO note that char-right won't enter a math inset from processLfun(),
        # but will from command minibuffer in Lyx!!! debug; even fails with:
        #    echo 'LYXCMD:clientname:char-right:' >~/.lyx/lyxpipe.in
        # If inside the math inset, the char-right pops to the outside left!
        #if self.insideMathInset(): print("debug inside math inset") # debug test
        #else: print("debug not inside math inset")

        # now test if we are inside a Lyx Notebook cell
        if not self.insideCell(): # no output cell immediately follows
            if createIfNecessary: # create a new output cell
                self.charLeft() # undo char-right in test above (end just outside cell)
                # The line below handles the special case of end of buffer insert.
                if self.insideCell(): self.charRight()
                # Now insert the output cell.
                # Note that flex-insert adds the "Flex:" prefix on the cell name.
                self.processLfun("command-sequence",
                                 "flex-insert LyxNotebookCell:Output:"
                                 + insetSpecifier+";inset-toggle open")
            else:
                # if we don't create a new cell, go back inside the previous one
                self.charLeft()
                if not self.insideCell(): self.charLeft() # handles end of buffer, too
                # note we currently stay at the end of inset, but could goto beginning
                return
        self.replaceCurrentCellText(lineList, assertInsideCell=True)
        if gotoBeginAfter:
            self.gotoCellBegin(assertInsideCell=True)
        return

    def replaceCurrentCellText(self, lineList,
                               gotoBeginAfter=False, assertInsideCell=False):
        r"""Replace the current cell's text with the lines in lineList
        Currently lineList can be a Cell, but it can also just be a list since
        no special Cell extra data is used.  The lines in lineList must be
        newline terminated, but should not include any \begin and \end Latex
        markup lines for the cell type."""

        # Write to a file and then read it in all at once, replacing selected text.
        # This gives better undo behavior than a self-insert for each line.
        if not assertInsideCell:
            if not self.insideCell(): return # not even in a cell

        if len(lineList) == 0:
            lineList = [""] # cells always have at least one line

        tmpFileName = open(self.tempCellWriteFile, "w")

        # process all but the last line (we know it has at least one)
        if len(lineList) > 1:
            for line in lineList[0:-1]:
                tmpFileName.write(line)

        # process the last line; strip off the newline so it displays right when read in
        strippedLastLine = lineList[-1].rstrip("\n") # debug changed from plain strip
        deleteSpace = False
        if strippedLastLine == "": # we cannot write and read a single empty string
            strippedLastLine = " " # so write a space, to delete later
            deleteSpace = True

        # write out to a temp file
        tmpFileName.write(strippedLastLine)
        tmpFileName.close()

        # read file into lyx, deleting space if it was inserted in special case above
        self.replaceCurrentCellTextFromPlaintextFile(self.tempCellWriteFile,
                                                     assertInsideCell=assertInsideCell)
        if deleteSpace: self.processLfun("char-delete-backward")

        # clean up by deleting the temporary file
        os.remove(self.tempCellWriteFile)
        if gotoBeginAfter:
            self.gotoCellBegin(assertInsideCell=True)
        return

    def replaceCurrentCellTextFromPlaintextFile(self, filename,
                                                assertInsideCell=False):
        """Replaces the cell's text with the contents of file filename."""
        if not assertInsideCell:
            if not self.insideCell(): return

        # select everything in the inset, to be replace by the file-insert
        self.processLfun("inset-select-all") # faster than the three lines above

        # read in the file, replacing selected text
        # self.processLfun("file-insert-plaintext-para", filename) # ignores newlines!
        self.processLfun("file-insert-plaintext", filename)
        return

    def writeAllCellCodeToFile(self, dataTupleList):
        """Sequentially writes all the cell code to output files, with cells of
        each insetSpecifier type being written to a different file, and where the
        init cells are written before the standard cells.  The format for
        dataTupleList is a list of tuples of the form
           (filename, insetSpecifier, commentLineBegin)
        The calling routine should figure out the dataTuple information, since
        this module does not have access to interpreterSpec data.  Currently
        will silently overwrite filename.  If comment-line char is set to a
        non-empty value then extra information to be written to the file in
        comments."""

        # update the Latex and get the name of the file it was exported to
        (currentBufferFileDirectory,
         currentBufferFilename,
         autoSaveFilename,
         fullPath) = self.getUpdatedLyxDirectoryData()

        # get all the cells and open the file with name filename
        allCells = self.getAllCellText()
        # some test lines for debugging below
        #allCells = self.getAllCellTextFromLatex(mostRecentLatexExport)
        #allCells = self.getAllCellTextFromLyxFile(currentBufferFilename)

        # loop through all the inset types, writing the cells for that type
        for filename, insetSpecifier, commentLineBegin in dataTupleList:

            # don't write if no cells of the particular type
            cells = [c for c in allCells if c.getCellType()[1] == insetSpecifier]
            if len(cells) == 0: continue

            # write an informative header comment to the file
            codeOutFile = open(filename, "w")
            bannerLine = commentLineBegin + "="*70
            now = datetime.datetime.now()
            if commentLineBegin: # don't write if commentLineBegin string is empty
                codeOutFile.write("\n" + bannerLine + "\n")
                msg = commentLineBegin + " File of all " + insetSpecifier \
                    + " cells from LyX Notebook source file:\n" \
                      + commentLineBegin + "    " + currentBufferFilename + "\n" \
                      + commentLineBegin + " " + now.strftime("%Y-%m-%d %H:%M")
                codeOutFile.write(msg)
                codeOutFile.write("\n" + bannerLine + "\n\n")

            # write the cells of the insetSpecifier type to the file
            for basicCellType in ["Init", "Standard"]:
                count = 0
                for cell in allCells:
                    cellType = cell.getCellType()
                    if cellType[0] == basicCellType and cellType[1] == insetSpecifier:
                        count += 1
                        if commentLineBegin: # don't write if empty commentLineBegin string
                            codeOutFile.write("\n" + bannerLine + "\n")
                            msg = commentLineBegin + " " + basicCellType + \
                                " cell number " + str(count) + "."
                            codeOutFile.write(msg)
                            codeOutFile.write("\n" + bannerLine + "\n\n")
                        for line in cell:
                            codeOutFile.write(line)
            codeOutFile.close()
        return

    def insertMostRecentGraphicAsInset(self):
        """Find the most recent graphics file in the current buffer's directory
        and insert it as a graphics inset at the current Lyx cursor point."""

        # general data about file suffixes recognized as graphics formats
        graphicExtensions = ".emf,.eps,.jpeg,.jpg,.pdf,.png,.ps,.raw,.rgba,.svg,.svgz"

        # get the dir of the current buffer and change directories to it
        dirData = self.getUpdatedLyxDirectoryData(autoSaveUpdate=False)

        # find most recent graphics file
        maxMtime = 0
        mostRecent = ""
        for dirpath, subdirs, files in os.walk(dirData[0]):
            for fname in files:
                fnameRoot, extension = os.path.splitext(fname)
                if not (extension in graphicExtensions): continue
                fullPath = os.path.join(dirpath, fname)
                mtime = os.stat(fullPath).st_mtime # or can use os.path.getmtime()
                if mtime > maxMtime:
                    maxMtime = mtime
                    # set mostRecent to path relative to current dir, for portability
                    mostRecent = os.path.relpath(fullPath)

        # old implementation in comment-string below works, not as portable, Unix-based
        """
        # Note the last char in options to ls is the number 1, not the letter l.
        lsCmd = r"ls -ct1 *.{" + graphicFormats + "} 2>/dev/null"
        f = os.popen(lsCmd)
        mostRecent = f.readline().strip() # get first listed, strip off whitespace (\n)
        """

        if mostRecent == "":
            print("No graphics files found in current directory!")
            return
        print("Inserting inset for most recent graphics file, " + mostRecent +
              ", at the cursor point (assuming the operation is allowed).")
        # could set height, too, but may affect aspect ratio
        # lyxscale is the percent scaling of the display in Lyx
        graphStr = r"graphics lyxscale 100 width 5in keepAspectRatio filename " \
            + mostRecent
        self.processLfun("inset-insert", graphStr)
        return

"""
Reference Material

Note that LFUNs can be tested and experimented with by typing them into the Lyx
command buffer (View->Toolbars->CommandBuffer).


Below are some possibly useful LFUNs which are implemented, with a few notes on
their usage.  Comments refer to Lyx 2.0.3 behavior.

   layout-module-add <MODULE>   # add a module.... maybe do auto, probably not...
   repeat <count> <LFUNcommand>  # repeat LFUN count times
   escape       # clears selection, if no selection then LFUN_FINISHED_FORWARD
                # but there is no command finished-forward (or backward, etc.)
   mark-off  # disable selection in region (with escape may get finished-forward)
   mark-on   # enable selection in region
       # neither mark-off or mark-on seem to do anything from command-buffer
   layout <layout> # sets layout for current para; layouts are top-left menu things
       # written there before dropping down; "Plain Layout" for listings and
       # "Standard Layout" for ordinary text regions.
   message <string>  # display the message in the status bar
   inset-begin   # goto beginning unless already there, in that case go to outer begin
   inset-end     # goto end unless already there, in that case go to outer end
   inset-select-all    # select the entire contents of the inset
   server-notify       # should be bound in Lyx, to command keys for external app
   newline-insert
   self-insert <STRING> # just inserts the string
   flex-insert <TYPE NAME>    # insert a FLEX inset, but the name should leave off
                              # the FLEX: prefix, since that is added automatically
   inset-insert <TYPE NAME> <ARGS>    # insert an ordinary inset
   char-delete-forward
   char-delete-backward
   line-delete
   word-delete-forward
   word-delete-backward
   inset-forall <TYPE NAME> <LFUN-COMMAND>   # type is, e.g., Flex:WrapListings for
               # a custom inset named Flex:WrapListings
   command-sequence <semicolon separated commands>
      # would this have problems semis in string arguments like in "self-insert xx;"?
   server-goto-file-row <FILE[.ext]> <ROW_NUMBER>
      # Examples from the docs:
      #    server-goto-file-row /home/user/example.lyx 41
      #    server-goto-file-row /tmp/lyx_tmpdir.XM3088/lyx_tmpbuf0/example.tex 41
      # Note this LFUN can go right to the line with the begin{} statement for a
      # cell, and positions to before the cell, but cannot go inside the insets
      # (i.e., line numbers inside listings-type insets don't work).
      # Note file *must* be in the Lyx temp dir, as far as I can get it to work,
      # and the .tex suffix must be used.
      # Adding lines earlier in Lyx files seems not to break it (i.e., doesn't
      # seem to require re-export to Latex.)  What actions require re-export is
      # unclear...
   undo
   redo
   cut
   copy
   selection-paste
   char-forward
   word-forward
   char-backward
   word-backward
   char-right          <--- arrow keys bound to these
   char-left           <--- arrow keys bound to these
   up
   down
   line-begin
   line-end
   buffer-begin
   buffer-end
   get-buf-name ???
   server-set-xy     # refers to the "editing area" and seems to act strangely
   server-get-xy     # BROKEN crashes Lyx 2.0.3 in some cases (reported as bug)
   word-replace      # BROKEN cannot enter the required \n newline chars between items
   word-find-forward
   word-find-backward
   paragraph-goto  # not well documented, works by "paragraph id"
   paragraph-params-apply <INDENT> <SPACING> <ALIGN> <OTHERS>
   inset-toggle <open|close|toggle|assign>    # applies to current cursor point
   server-get-layout
          # Get the name of the current layout (that is environment) at the cursor
          # position.  Returns "Plain Layout" for listings-type insets, "Standard"
          # for ordinary, "Enumerate" for enumerates.  This is very useful in
          # faking LFUNs that don't exist.
   layout <layout>  # Sets the layout (that is, environment) for the current paragraph
   newline-insert <newline|linebreak>    # default is newline
   file-insert [<FILE>]
      # inserts another Lyx file... may be useful, depending on the details
   file-insert-plaintext [<FILE>]      # these are good for insert, since one undo
   file-insert-plaintext-para [<FILE>] # these are good for insert, since one undo
       # The file-insert commands REQUIRE full pathname to work correctly!!!!!!!!
       # ALSO, para becomes CR in listings, so files need to be written with blank
       # lines (like double spacing).
       # The plaintext-para version ignores empty lines in files, so use ordinary
       # version to preserve them
   unicode-insert <hex code>     # Sample: unicode-insert 0x0100
       # this might be useful for a short and obscure cookie sequence....
       # To insert a space: unicode-insert 0x0020

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
   get-current-inset-type            -- the name of the inset type, i.e. Listings
   goto-next-inset <type>            -- go to next inset of that type
   inset-begin and inset-end mod     -- versions that are idempotent and stay inside
   get-lyx-version                   -- the version of Lyx in case it matters
                                          (like if new lfuns become available)

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
But now the easyGUI menu does that.

-- Some way to detect which branch you are in, or to get current branch info
and specify branch-applicability in commands.  This might be useful, for
example, to have a branch for code where vpython was available, and a
branch where it wasn't.

-- Embedded Python would also be very nice, if that ever gets included (has been
discussed on the Lyx lists several times).  At least some kind of conditional
structure on LFUNs might be helpful in some instances.
"""

#
# Testing code for this module.
#

if __name__ == "__main__":
    print("------------- starting tests ------------------------")

    lyxProcess = InteractWithLyxCells("interpreterCellsApp")

    #print("started the interact, now get and print Lyx's filename")
    #print(lyxProcess.serverGetFilename())
    #print(lyxProcess.serverGetFilename())

    #print(lyxProcess.processLfun("server-get-layout"))

    #print(lyxProcess.gotoCellBegin())
    #print(lyxProcess.insertMagicCookie())
    #print(lyxProcess.exportLatexToLyxTempDir())

    #print(lyxProcess.insertMagicCookieForall())
    #print(lyxProcess.deleteAll("egg"))
    #print(lyxProcess.waitForServerNotify())
    #print(lyxProcess.gotoNextCell())
    #print(lyxProcess.insertMagicCookieForall())
    #print(lyxProcess.deleteMagicCookieForall())
    #print(lyxProcess.insertMagicCookieInsideForall())
    #print(lyxProcess.deleteMagicCookieInsideForall())

    #print("Are we inside a cell?", lyxProcess.insideCell())
    #print(lyxProcess.selfInsertLine("eggbert"))
    #print(lyxProcess.getUpdatedLyxDirectoryData())

    #lyxProcess.getAllCellTextFromLatex()
    #lyxProcess.getCurrentCellText()
    """
   while True:
      print(lyxProcess.waitForServerNotify())
      #lyxProcess.writeAllCellCodeToFile() # needs more args now
   """

    filename = "testInteractWithLyxCells.lyx"
    lyxProcess.getAllCellTextFromLyxFile(filename)

    """
   while True:
      print(lyxProcess.waitForServerNotify())
      lineList = ["I am the first line\n", "\n", "and I am the third line.\n", "four\n"]
      #lineList = ["\n"]
      lyxProcess.replaceCurrentCellText(lineList)
   """
    """
   while True:
      print(lyxProcess.waitForServerNotify())
      print(lyxProcess.insertMagicCookieInsideCurrent(onCurrentLine = True))
      print(lyxProcess.waitForServerNotify())
      #print(lyxProcess.deleteMagicCookieInsideCurrent(onCurrentLine = True))
      #print(lyxProcess.deleteMagicCookieInsideCurrent(assertCursorAtCookieEnd = True))
   """
    """
   while True:
      print(lyxProcess.waitForServerNotify())
      print(lyxProcess.gotoNextCell())
   """
    """
   while True:
      print(lyxProcess.waitForServerNotify())
      #print("xy coordinates:", lyxProcess.processLfun("server-get-xy")) # crash!
      # prints, but seemingly meaningless...
      print("xy coordinates:", lyxProcess.processLfun("server-set-xy", "10 10"))
   """

