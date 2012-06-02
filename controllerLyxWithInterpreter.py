"""
=========================================================================
This file is part of LyX Notebook, which works with LyX (and is licensed 
in the same way) but is an independent project.  License details (GPL V2) 
can be found in the file COPYING.

Copyright (C) 2012 Allen Barker
=========================================================================

This is the main module of the Lyx Notebook program; the lyxNotebook.py script
just does basic startup stuff like making sure a Lyx Notebook process is not
already running.

This module contains the implementation of the high-level controller class
ControllerLyxWithInterpreter.  This class mediates between the Lyx program and
one or more interpreters for interpreting code.  It gets basic commands from
Lyx, executes them, and pushes the appropriate actions back to Lyx.  Some of
these actions involve running code in an interpreter.  In these cases, the
controller sends the code to the appropriate interpreter, gets the results
back, and then pushes the results to Lyx.
"""

from __future__ import print_function, division
import easygui as eg
import re
import sys, os, time, signal

# local file imports
from interactWithLyxCells import InteractWithLyxCells, Cell
from externalInterpreter import ExternalInterpreter
import interpreterSpecs # specs for all the interpreters which are allowed
import keymap # the current mapping of keys to Lyx Notebook functions
import lyxNotebookUserSettings

class IndentCalc(object):
   """A class that is used for Python cells, to calculate the indentation levels.
   This is used so that users can write code like in a file, without the extra
   blank lines which are often required in the interpreter.  A blank line is
   sent automatically when the code indentation level reaches zero, going downward.
   
   The class must calculate explicit and implicit line continuations, since this
   affects the indentation calculation.   The indentation is also incremented
   if a colon is found on a line but not in a comment, string, or within any
   parens, curly braces, or brackets.  This is to handle one-liners like 
      "if x==4: return"
   The calculated indententation values are no longer strictly correct literally, 
   but they still works in the "down to zero" calculation, which is what is 
   important.
   
   An instance of this object should be passed each physical line, one by one.  
   It then makes calculations concerning the logical line structure.  There 
   are no side effects, so results can be ignored for non-Python code."""
   def __init__(self):
      self.reset()

   def reset(self):
      self.parens = 0
      self.brackets = 0
      self.curlys = 0
      self.inString1 = False
      self.inString2 = False
      self.backslashContinuation = False
      self.indentationLevel = 0
      self.indentationLevelDownToZero = False

   def inStringLiteral(self):
      return self.inString1 or self.inString2
   
   def inParenBracketCurly(self):
      return self.parens > 0 or self.brackets > 0 or self.curlys > 0

   def inExplicitLineContinuation(self):
      return self.backslashContinuation

   def inImplicitLineContinuation(self):
      return self.inParenBracketCurly() or self.inString2

   def inLineContinuation(self):
      return self.inExplicitLineContinuation() or self.inImplicitLineContinuation()

   def indentLevel(self):
      return self.indentationLevel

   def indentLevelDownToZero(self):
      return self.indentationLevelDownToZero

   def updateForPhysicalLine(self, codeLine):
      """The IndentCalc class should be sequentially passed physical lines, via
      this function."""
      
      # "indentation down to zero" is only considered true right after the first 
      # non-continued physical line which has indentation level zero when the
      # previous line had a higher level, so always reset for each physical line
      self.indentationLevelDownToZero = False

      # detect a blank line (possibly with a comment) and do nothing else
      strippedLine = codeLine.rstrip() # strip off trailing whitespace
      if len(strippedLine) == 0: 
         self.backslashContinuation = False # assume blanks unset explicit continuation
         return
      firstNonwhitespace = re.search("\S", strippedLine)
      if firstNonwhitespace == "#": 
         self.backslashContinuation = False
         return

      # update the indentation level (unless line is continued)
      if not self.inLineContinuation():
         newLevel = firstNonwhitespace.start()
         if self.indentationLevel > 0 and newLevel == 0:
            self.indentationLevelDownToZero = True
         self.indentationLevel = newLevel
      
      # backslash continuation only holds for one line (unless reset later at end)
      # this was already used in calculating self.inLineContinuation() above
      self.backslashContinuation = False 

      # go through each char in the line, updating paren counts, etc.
      # note that i is the index into the line strippedLine
      backslashEscape = False
      # fake a C-style loop, so we can jump ahead easily by resetting i
      i = -1 
      while True:

         i += 1
         if i >= len(strippedLine): break
         char = strippedLine[i]

         # first handle backslash escape mode... we always ignore the next char,
         # and the only cases we care about are one-character backslash escapes
         # (let Python worry about any syntax errors with backslash outside strings)
         if backslashEscape:
            backslashEscape = False
            continue

         # handle the backslash char, either line continuation or escape
         if char == "\\":
            if i == len(strippedLine) - 1: # line continuation
               self.backslashContinuation = True
               continue # could also break, since at end of line
            else: # start a backslash escape
               # this is only valid in strings, but let Python catch any errors there
               backslashEscape = True
               continue
               
         # look for string delimiters and toggle string modes
         if char == "\"":
            # if in a string, then we got the closing quote
            if self.inString1: self.inString1 = False
            # check if this is part of a triple-quote string
            elif (i <= len(strippedLine) - 3 and 
                  strippedLine[i+1] == "\"" and strippedLine[i+2] == "\""):
               if self.inString2: self.inString2 = False
               else: self.inString2 = True
               i += 2 # increment past the second two quotes of the triple-quote
            # otherwise we start a new single-quote string
            else: self.inString1 = True
            continue

         # ignore all else inside strings
         if self.inStringLiteral(): continue 

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
         if char == ":" and not self.inParenBracketCurly(): self.indentationLevel += 3
      return


class InterpreterProcess(object):
   """An instance of this class represents a data record for a running
   interpreter process.  Contains an ExternalInterpreter instance for that
   process, but also has an IndentCalc instance, and keeps track of the most
   recent prompt received from the interpreter."""
   def __init__(self, spec):
      self.spec = spec
      self.mostRecentPrompt = self.spec["mainPrompt"]
      self.indentCalc = IndentCalc()
      self.externalInterp = ExternalInterpreter(self.spec)


class InterpreterProcessCollection(object):
   """A class to hold multiple InterpreterProcess instances.  There will
   probably only be a single instance, but multiple instances should not cause
   problems.  Basically a dict mapping (bufferName,insetSpecifier) tuples to
   InterpreterProcess class instances.  Starts processes when necessary."""
   def __init__(self, currentBuffer):
      if lyxNotebookUserSettings.separateInterpretersForEachBuffer == False:
         currentBuffer = "___dummy___" # force all to use same buffer if not set
      self.interpreterSpecList = [ specName.params
            for specName in interpreterSpecs.allSpecs ]
      self.numSpecs = len(self.interpreterSpecList)
      self.insetSpecifierToInterpreterSpecDict = {}
      self.allInsetSpecifiers = []
      for spec in self.interpreterSpecList:
         self.insetSpecifierToInterpreterSpecDict[spec["insetSpecifier"]] = spec
         self.allInsetSpecifiers.append(spec["insetSpecifier"])
      self.resetAllInterpretersForAllBuffers(currentBuffer)

   def resetAllInterpretersForAllBuffers(self, currentBuffer=""):
      """Reset all the interpreters, restarting any not-on-demand ones for the
      buffer currentBuffer (unless it equals the empty string).  This also
      frees any processes for former buffers, such as for closed buffers and
      renamed buffers."""
      self.mainDict = {} # map (bufferName,insetSpecifier) tuple to InterpreterProcess
      # Start up not-on-demand interpreters, but only for the current buffer
      # (in principle we could use buffer-next to get all buffers and start for all, 
      # but they may not all even # use Lyx Notebook).
      if currentBuffer != "":
         self.resetForBuffer(currentBuffer)

   def resetForBuffer(self, bufferName, insetSpecifier=""):
      """Reset the interpreter for insetSpecifier cells for buffer bufferName.  
      Restarts the whole process.  If insetSpecifier is the empty string then 
      reset for all inset specifiers."""
      if lyxNotebookUserSettings.separateInterpretersForEachBuffer == False:
         bufferName = "___dummy___" # force all to use same buffer if not set
      insetSpecifierList = [ insetSpecifier ]
      if insetSpecifier == "": # do all if empty string
         insetSpecifierList = self.allInsetSpecifiers
      for insetSpecifier in insetSpecifierList:
         key = (bufferName, insetSpecifier)
         spec = self.insetSpecifierToInterpreterSpecDict[insetSpecifier]
         if key in self.mainDict: del self.mainDict[key]
         if not spec["runOnlyOnDemand"]: 
            self.getInterpreterProcess(bufferName, insetSpecifier)

   def getInterpreterProcess(self, bufferName, insetSpecifier):
      """Get interpreter process, creating/starting one if one not there already."""
      if lyxNotebookUserSettings.separateInterpretersForEachBuffer == False:
         bufferName = "___dummy___" # force all to use same buffer if not set
      key = (bufferName, insetSpecifier)
      if not key in self.mainDict:
         msg = "Starting interpreter for " + insetSpecifier
         if lyxNotebookUserSettings.separateInterpretersForEachBuffer == True: 
            msg += ", for buffer:\n   " + bufferName
         print(msg)
         self.mainDict[key] = InterpreterProcess(
               self.insetSpecifierToInterpreterSpecDict[insetSpecifier])
      return self.mainDict[key]

   def printStartMessage(self):
      startMsg = "Running for " + str(self.numSpecs) + \
            " possible interpreters (cell languages):\n"
      interpStr = ""
      for i in range(self.numSpecs):
         interpStr += "      " + self.interpreterSpecList[i]["insetSpecifier"]
         interpStr += " (label=\"" + self.interpreterSpecList[i]["progName"] + "\""
         if not self.interpreterSpecList[i]["runOnlyOnDemand"]:
            interpStr += ", autostarted in current buffer"
         interpStr += ")\n"
      startMsg += interpStr
      print(startMsg)
      

class ControllerLyxWithInterpreter(object):
   """This class is the high-level controller class which deals with user
   interactions and which manages the Lyx process and the interpreter processes.
   The interpreter specifications are read from the module interpreterSpecs.  The 
   list interpreterSpecs.allSpecs in that module is assumed to contains all the 
   specs."""
   def __init__(self, clientname):

      self.noEcho = lyxNotebookUserSettings.noEcho
      self.bufferReplaceOnBatchEval = lyxNotebookUserSettings.bufferReplaceOnBatchEval

      # Set up interactions with Lyx.
      self.clientname = clientname
      self.lyxProcess = InteractWithLyxCells(clientname) 

      # Initialize the collection of interpreter processes.
      self.allInterps = InterpreterProcessCollection(
            self.lyxProcess.serverGetFilename()) # buffer name is file name
      self.allInterps.printStartMessage()

      # Display a startup notification message in Lyx.
      message = "LyX Notebook is now running..."
      self.lyxProcess.showMessage(message)
      #self.displayPopupMessage(message=message, text=startMsg, seconds=3)

      # Start up the command loop.
      self.serverNotifyLoop()
      return # never executed; command loop above continues until sys.exit

   def resetInterpretersForBuffer(self, bufferName=""):
      """Reset all the interpreters for the buffer, starting completely new processes 
      for them.  If bufferName is empty the current buffer is used."""
      if bufferName == "": bufferName = self.lyxProcess.serverGetFilename()
      self.allInterps.resetForBuffer(bufferName)
      return

   def resetAllInterpretersForAllBuffers(self):
      """Reset all the interpreters for all buffers, starting not-on-demand
      interpreters for the current buffer."""
      currentBuffer = self.lyxProcess.serverGetFilename()
      self.allInterps.resetAllInterpretersForAllBuffers(currentBuffer)
      return

   def serverNotifyLoop(self):
      """This is the main command loop, getting commands from Lyx and executing 
      them."""

      self.keymap = dict(keymap.allCommandsAndKeymap) # dict mapping keys to commands

      while True:
         # wait for a bound key in Lyx to be pressed, and get it when it is
         keyPressed = self.lyxProcess.waitForServerNotify()
         if not keyPressed in self.keymap: continue # server-notify on non-command

         # eat any buffered events (notify or otherwise): avoid annoying user
         self.lyxProcess.getServerEvent(info=False, error=False, notify=False)
         
         # look up the action for the key
         keyAction = self.keymap[keyPressed]

         # =====================================================================
         # First, look for submenu call; open menu and reset keyAction if found.
         # =====================================================================

         if keyAction == "pop up submenu": # handle the pop-up menu option first
            choices = []
            count = 0
            for (key,command) in keymap.allCommandsAndKeymap:
               count += 1 # easyGUI is limited in display; count keeps list ordered
               if key != None:
                  key = key.replace("Shift+","S-") # this is to align columns
                  key += "_"*(8-len(key))
               else: 
                  key = "_"*8
               countStr = str(count).zfill(2) + "_"*5
               choices.append(countStr + key + "_"*5 + " " + command)
            choiceStr = eg.choicebox(
                  msg="Choose an action or click 'cancel'...", 
                  title="LyX Notebook Submenu",
                  choices = choices
                  )
            if choiceStr == None: continue
            choiceStr = choiceStr.split("_ ")[-1]
            keyAction = choiceStr

         # ====================================================================
         # Handle the general key actions, including commands set from submenu.
         # ====================================================================
         
         #
         # Goto cell commands.
         #

         if keyAction == "goto next any cell": 
            self.lyxProcess.showMessage("going to next cell")
            self.lyxProcess.openAllCells() # gotoNextCell() needs open cells for now
            self.lyxProcess.gotoNextCell()
            # self.lyxProcess.gotoNextCell2() # alternate implementation, experimental
         
         elif keyAction == "goto prev any cell":
            self.lyxProcess.showMessage("going to previous cell")
            self.lyxProcess.openAllCells() # gotoPrevCell() needs open cells for now
            self.lyxProcess.gotoPrevCell()
         
         elif keyAction == "goto next code cell": 
            self.lyxProcess.showMessage("going to next code cell")
            self.lyxProcess.openAllCells() # gotoNextCell() needs open cells for now
            self.lyxProcess.gotoNextCell(output=False)
         
         elif keyAction == "goto prev code cell":
            self.lyxProcess.showMessage("going to previous code cell")
            self.lyxProcess.openAllCells() # gotoPrevCell() needs open cells for now
            self.lyxProcess.gotoPrevCell(output=False)
         
         elif keyAction == "goto next init cell": 
            self.lyxProcess.showMessage("going to next init cell")
            self.lyxProcess.openAllCells() # gotoNextCell() needs open cells for now
            self.lyxProcess.gotoNextCell(standard=False, output=False)
         
         elif keyAction == "goto prev init cell":
            self.lyxProcess.showMessage("going to prev init cell")
            self.lyxProcess.openAllCells() # gotoPrevCell() needs open cells for now
            self.lyxProcess.gotoPrevCell(standard=False, output=False)
         
         elif keyAction == "goto next standard cell": 
            self.lyxProcess.showMessage("going to next standard cell")
            self.lyxProcess.openAllCells() # gotoNextCell() needs open cells for now
            self.lyxProcess.gotoNextCell(init=False, output=False)
         
         elif keyAction == "goto prev standard cell":
            self.lyxProcess.showMessage("going to prev standard cell")
            self.lyxProcess.openAllCells() # gotoPrevCell() needs open cells for now
            self.lyxProcess.gotoPrevCell(init=False, output=False)
         
         #
         # Ordinary cell-evaluate commands, done explicitly in Lyx.
         #

         elif keyAction == "evaluate current cell":
            self.lyxProcess.showMessage("evaluating the current cell")
            self.evaluateLyxCell()
         
         elif keyAction == "evaluate current cell after reinit":
            self.lyxProcess.showMessage("evaluating the current cell after reinit")
            print("Restarting all interpreters, single-interp restart unimplemented.")
            self.resetInterpretersForBuffer() # TODO currently restarts them all
            self.evaluateLyxCell()
         
         elif keyAction == "evaluate all code cells":
            self.lyxProcess.showMessage("evaluating the all code cells")
            self.evaluateAllCodeCells()
         
         elif keyAction == "evaluate all code cells after reinit":
            self.lyxProcess.showMessage("evaluating all code cells after reinit")
            self.resetInterpretersForBuffer() 
            self.evaluateAllCodeCells()
         
         elif keyAction == "evaluate all init cells":
            self.lyxProcess.showMessage("evaluating all init cells")
            self.evaluateAllCodeCells(standard=False)
         
         elif keyAction == "evaluate all init cells after reinit":
            self.lyxProcess.showMessage("evaluating all init cells after reinit")
            self.resetInterpretersForBuffer() 
            self.evaluateAllCodeCells(standard=False)
         
         elif keyAction == "evaluate all standard cells":
            self.lyxProcess.showMessage("evaluating all standard cells")
            self.evaluateAllCodeCells(init=False)
         
         elif keyAction == "evaluate all standard cells after reinit":
            self.lyxProcess.showMessage("evaluating all standard cells after reinit")
            self.resetInterpretersForBuffer() 
            self.evaluateAllCodeCells(init=False)
         
         #
         # Batch evaluation commands.
         #
         # TODO: could clean up and move bufferReplaceOnBatchEval conditionals to the
         # replaceCurrentBufferFile function (after renaming it slightly)

         elif keyAction == "toggle buffer replace on batch eval":
            self.bufferReplaceOnBatchEval = not self.bufferReplaceOnBatchEval
            self.lyxProcess.showMessage("toggled buffer replace on batch eval to: " 
                  + str(self.bufferReplaceOnBatchEval))

         elif keyAction == "revert to most recent batch eval backup":
            self.revertToMostRecentBatchEvalBackup(messages=True)

         elif keyAction == "batch evaluate all code cells":
            toFileName = self.batchEvaluateAllCodeCellsToLyxFile(
                  init=True, standard=True, messages=True)
            if not self.bufferReplaceOnBatchEval:
               self.lyxProcess.processLfun("file-open", toFileName)
            else:
               self.replaceCurrentBufferFile(toFileName, 
                     reloadBuffer=True, messages=True)

         elif keyAction == "batch evaluate all code cells after reinit":
            self.resetInterpretersForBuffer() 
            toFileName = self.batchEvaluateAllCodeCellsToLyxFile(
                  init=True, standard=True, messages=True)
            if not self.bufferReplaceOnBatchEval:
               self.lyxProcess.processLfun("file-open", toFileName)
            else:
               self.replaceCurrentBufferFile(toFileName, 
                     reloadBuffer=True, messages=True)

         elif keyAction == "batch evaluate all init cells":
            toFileName = self.batchEvaluateAllCodeCellsToLyxFile(
                  init=True, standard=False, messages=True)
            if not self.bufferReplaceOnBatchEval:
               self.lyxProcess.processLfun("file-open", toFileName)
            else:
               self.replaceCurrentBufferFile(toFileName, 
                     reloadBuffer=True, messages=True)

         elif keyAction == "batch evaluate all init cells after reinit":
            self.resetInterpretersForBuffer() 
            toFileName = self.batchEvaluateAllCodeCellsToLyxFile(
                  init=True, standard=False, messages=True)
            if not self.bufferReplaceOnBatchEval:
               self.lyxProcess.processLfun("file-open", toFileName)
            else:
               self.replaceCurrentBufferFile(toFileName, 
                     reloadBuffer=True, messages=True)

         elif keyAction == "batch evaluate all standard cells":
            toFileName = self.batchEvaluateAllCodeCellsToLyxFile(
                  init=False, standard=True, messages=True)
            if not self.bufferReplaceOnBatchEval:
               self.lyxProcess.processLfun("file-open", toFileName)
            else:
               self.replaceCurrentBufferFile(toFileName, 
                     reloadBuffer=True, messages=True)

         elif (keyAction == 
               "batch evaluate all standard cells after reinit"):
            self.resetInterpretersForBuffer() 
            toFileName = self.batchEvaluateAllCodeCellsToLyxFile(
                  init=False, standard=True, messages=True)
            if not self.bufferReplaceOnBatchEval:
               self.lyxProcess.processLfun("file-open", toFileName)
            else:
               self.replaceCurrentBufferFile(toFileName, 
                     reloadBuffer=True, messages=True)

         #
         # Misc. commands.
         #

         elif keyAction == "reinitialize current interpreter":
            print("Not implemented, restarting all interpreters.")
            self.resetInterpretersForBuffer() 
            # TODO, currently restarts all: need to look up current interp
            self.lyxProcess.showMessage("all interpreters reinitialized")
         
         elif keyAction == "reinitialize all interpreters for buffer":
            self.resetInterpretersForBuffer() 
            self.lyxProcess.showMessage("all interpreters for buffer reinitialized")
         
         elif keyAction == "reinitialize all interpreters for all buffers":
            self.resetAllInterpretersForAllBuffers() 
            self.lyxProcess.showMessage(
                  "all interpreters for all buffer reinitialized")
         
         elif keyAction == "write all code cells to files":
            filePrefix = self.lyxProcess.serverGetFilename()
            if filePrefix.rstrip()[-4:] != ".lyx": continue
            filePrefix = filePrefix.rstrip()[0:-4]
            dataTupleList = []
            for spec in self.allInterps.interpreterSpecList:
               # currently the interactWithLyx module does not make use of any
               # of the interpreterSpec data or its format, so we need to
               # look some things up to pass in
               insetSpecifier = spec["insetSpecifier"]
               fileSuffix = spec["fileSuffix"]
               # data tuple format is (filename, insetSpecifier, commentBeginChar)
               dataTupleList.append((
                     filePrefix + ".allcells." + insetSpecifier + fileSuffix,
                     insetSpecifier,
                     spec["commentLine"]
                     ))
            self.lyxProcess.writeAllCellCodeToFile(dataTupleList)
            self.lyxProcess.showMessage("all code cells were written to files")
         
         elif keyAction == "insert most recent graphic file":
            self.lyxProcess.insertMostRecentGraphicAsInset()
            self.lyxProcess.showMessage("inserted the most recent graphic file")
         
         elif keyAction == "kill lyx notebook process":
            self.lyxProcess.showMessage("killing LyX Notebook process")
            sys.exit(0)

         elif keyAction == "prompt echo on":
            self.noEcho = False
            self.lyxProcess.showMessage("set prompt echo to False")
         
         elif keyAction == "prompt echo off":
            self.noEcho = True
            self.lyxProcess.showMessage("set prompt echo to True")
         
         elif keyAction == "toggle prompt echo":
            self.noEcho = not self.noEcho
            message = "toggled prompt echo to " + str(not self.noEcho)
            self.lyxProcess.showMessage(message)
                 
         elif keyAction == "evaluate newlines as current cell":
            self.evaluateLyxCell(justSendNewlines=True)
            self.lyxProcess.showMessage("evaluated newlines as current cell")

         #
         # Commands to open and close cells.
         #

         elif keyAction == "open all cells":
            self.lyxProcess.openAllCells()
            self.lyxProcess.showMessage("opened all cells")
         
         elif keyAction == "close all cells":
            self.lyxProcess.closeAllCellsButCurrent()
            self.lyxProcess.showMessage("closed all cells")
         
         elif keyAction == "open all output cells":
            self.lyxProcess.openAllCells(init = False, standard = False)
            self.lyxProcess.showMessage("opened all output cells")
         
         elif keyAction == "close all output cells":
            self.lyxProcess.closeAllCellsButCurrent(init = False, standard = False)
            self.lyxProcess.showMessage("closed all output cells")
         
         else:
            pass # ignore command from server-notify if it is not recognized
      return # never executed; loop forever or sys.exit

   def evaluateAllCodeCells(self, init=True, standard=True):
      """Evaluate all cells.  Quits evaluation between cells if any Lyx Notebook
      command key is pressed (any key bound to server-notify).  The flags can
      be used to only evaluate certain types of cells."""

      # first set up code to check between cell evals whether user wants to halt

      # initialize the relevant flag in the lyxProcess class
      self.lyxProcess.ignoredServerNotifyEvent = False
      # eat any server events from Lyx (after the NOTIFY command to do the eval)
      self.lyxProcess.getServerEvent(info=False, error=False, notify=False)

      # define a local function to check and query the user if a NOTIFY was ignored
      def checkForIgnoredServerNotify():
         """Return True if a server-notify was ignored and user wants to quit."""
         # eat all events between cell evals, and check if NOTIFY was ignored
         self.lyxProcess.getServerEvent(info=False, error=False, notify=False)
         if self.lyxProcess.ignoredServerNotifyEvent == True:
            msg = "Halt multi-cell evaluation at the current point?"
            choices = (["Yes","No"])
            reply = eg.buttonbox(msg, choices=choices)
            if reply == "Yes":
               return True
            self.lyxProcess.ignoredServerNotifyEvent = False
         return False

      # now get cell count data and print a nice message
      (numInitCells, numStandardCells, numOutputCells) = \
            self.lyxProcess.getGlobalCellInfo()
      print("There are", numInitCells+numStandardCells, "code cells:", 
            numStandardCells, "Standard cells and", numInitCells, "Init cells.")
      if init and standard: print("Evaluating all the code cells.")
      elif init: print("Evaluating all the Init cells only.")
      elif standard: print("Evaluating all the Standard cells only.")

      # cycle through the Init cells and then the Standard cells, evaluating
      if init:
         if numInitCells > 0: 
            self.lyxProcess.gotoBufferBegin()
            self.lyxProcess.openAllCells(output=False, standard=False)
         for i in range(numInitCells):
            userWantsToHalt = checkForIgnoredServerNotify()
            if userWantsToHalt:
               print("Halting multi-cell evaluation before Init cell", i+1,
                     "(a key bound to\nserver-notify was pressed).")
               return
            self.lyxProcess.gotoNextCell(output=False, standard=False)
            self.evaluateLyxCell()
      if standard:
         if numStandardCells > 0: 
            self.lyxProcess.gotoBufferBegin()
            self.lyxProcess.openAllCells(output=False, init=False)
         for i in range(numStandardCells):
            userWantsToHalt = checkForIgnoredServerNotify()
            if userWantsToHalt:
               print("Halting multi-cell evaluation before Standard cell", i+1,
                     "(a key bound to\nserver-notify was pressed).")
               return
            self.lyxProcess.gotoNextCell(output=False, init=False)
            self.evaluateLyxCell()
      print("Finished multi-cell evaluation.")
      return

   def batchEvaluateAllCodeCellsToLyxFile(self, init=True, standard=True, 
         messages=False):
      """Evaluate all the cells of the flagged basic types, and then write them
      to an output .lyx file.  The filename of the new file is returned."""
      # TODO: also could print nice message to terminal like in regular routine

      if not init and not standard: return None
      if init and not standard: cellTypes = "Init"
      if not init and standard: cellTypes = "Standard"
      if init and standard: cellTypes = "Init and Standard"

      if messages: 
         self.lyxProcess.showMessage("Batch evaluating all %s cells." % (cellTypes,))
      # get all cell text from the Lyx auto-save file (saves it as a side effect)
      allCells = self.lyxProcess.getAllCellText(useLatexExport=False)
      
      # evaluate all the cells in the list (results pasted onto the cells)
      self.evaluateListOfCellClasses(allCells, init=init, standard=standard, 
            messages=messages)

      # get current directory data (also changes current directory to buffer's dir)
      currentDirData = self.lyxProcess.getUpdatedLyxDirectoryData()

      # calc the name of the auto-save file and the new .lyx file's name
      fromFileName = currentDirData[2] # prefer auto-save file
      if fromFileName == "": fromFileName =  currentDirData[1] # buffer's file
      toFileName = currentDirData[3][:-4] + ".newOutput.lyx"

      # create the new .lyx file from the evaluated list of cells
      self.lyxProcess.replaceAllCellTextInLyxFile(
            fromFileName, toFileName, allCells, init=init, standard=standard)

      if messages: 
         self.lyxProcess.showMessage(
               "Finished batch evaluation of all %s cells, wait for any buffer updates." 
               % (cellTypes,))
      return toFileName

   def evaluateListOfCellClasses(self, cellList, init=True, standard=True,
         messages=False):
      """Evaluates the list of Cell class instances, first the init cells and
      then the standard cells (unless one of the flags is set False).  Used for
      batch processing and faster evaluation of a group of cells.  The resulting
      output is pasted onto the cells in cellList as the data field 
      evaluationOutput.  The list cellList is returned as a convenience."""
      msg="Evaluating %s cell %s (%s cell)."
      if init:
         num = 0
         for cell in cellList:
            (basicType, insetSpec) = cell.getCellType()
            if basicType == "Init":
               num += 1
               if messages: self.lyxProcess.showMessage(msg%(basicType,num,insetSpec))
               self.evaluateCodeInCellClass(cell)
         if messages: 
            self.lyxProcess.showMessage("Finished Init cell evaluations.")
      if standard:
         num = 0
         for cell in cellList:
            (basicType, insetSpec) = cell.getCellType()
            if basicType == "Standard":
               num += 1
               if messages: self.lyxProcess.showMessage(msg%(basicType,num,insetSpec))
               self.evaluateCodeInCellClass(cell)
         if messages: 
            self.lyxProcess.showMessage("Finished Standard cell evaluations.")
      return cellList

   def evaluateLyxCell(self, justSendNewlines=False):
      """Evaluate the code cell at the current cursor position in Lyx.  Ignore if 
      not inside a code cell."""
      
      # get the code text from the current cell
      codeCellText = self.lyxProcess.getCurrentCellText()

      if codeCellText == None: return # not in a cell in the first place

      # check that cell is code (could just check output=None later, but do here, too)
      (basicType, insetSpecifierLanguage) = codeCellText.getCellType()
      if basicType == "Output": return # not a code cell

      # TODO: optional line wrapping at the Python level (but currently works OK
      # with listings).  Currently does nothing.  Can do the same with output 
      # text below, but not currently done.  Could also highlight if that
      # would display in inset and be removable for later evals.
      codeCellText = self.wrapLongLines(codeCellText) # do any line-wrapping

      # do the actual code evaluation and get the output
      output = self.evaluateCodeInCellClass(codeCellText, justSendNewlines)
   
      #
      # Replace the old output with the new output (and maybe replace input).
      # 

      """
      print("debug code list being replaced with:\n", codeCellText)
      print("debug end of code list being replaced with")
      print("debug code output being replaced with:\n", output)
      print("debug end of code output being replaced with")
      """

      # Rewrite input, might be useful for wrapping or formatting.
      # Bug on rewrite with empty last line!  Empty last lines are
      # ignored by listings when saving to Latex (and sometimes in the Lyx inset).
      # Thus they are not read in correctly after having been saved, and are not
      # printed.  So perhaps better not to display them in LyX: they won't print.
      rewriteCodeCells = True
      if rewriteCodeCells and not justSendNewlines:
         self.lyxProcess.replaceCurrentCellText(codeCellText, assertInsideCell = True)
      elif not justSendNewlines:
         # some blue selection-highlighting feedback even when text not replaced...
         self.lyxProcess.processLfun("inset-select-all")
         self.lyxProcess.processLfun("escape")

      # Note there is a bug in listings 1.3 at least: showlines=true doesn't work 
      # and will not show empty lines at the end of a listings box...  Adding spaces
      # or tabs on the line does not help, workaround of redefining formfeed in 
      # listings is apparently blocked by passthru Flex option.  So warn users, minor
      # bug remains.
      # if len(output) > 0 and output[-1] == "\n": output[-1] = "\f\n"

      (basicType, insetSpecifier) = codeCellText.getCellType()
      self.lyxProcess.replaceCurrentOutputCellText(output,
            assertInsideCell=True, insetSpecifier=insetSpecifier)
      return

   def evaluateCodeInCellClass(self, codeCellText, justSendNewlines=False):
      """Evaluate the lines of code in the Cell class instance codeCellText.
      The output is returned as a list of lines, and is also pasted onto the
      codeCellText instance as the data field evaluationOutput.  Returns
      None for a non-code cell."""

      (basicType, insetSpecifierLang) = codeCellText.getCellType()
      if basicType == "Output": # if not a code cell
         codeCellText.evaluationOutput = None
         return None

      # Find the appropriate interpreter to evaluate the cell.
      # Note that the insetSpecifier names are required to be unique.
      interpreterProcess = self.allInterps.getInterpreterProcess(
            self.lyxProcess.serverGetFilename(), insetSpecifierLang)
      interpreterSpec = interpreterProcess.spec

      # If the interpreterSpec defines a noopAtCellEnd then append it to the cell 
      # code.  Python can add "pass\n", for example, to always return to outer 
      # indent level.  Most languages will define it as None.
      noopAtCellEnd = interpreterSpec["noopAtCellEnd"]
      extraCodeLines = []
      if noopAtCellEnd: # doesn't run for None or "", since they eval to False
         extraCodeLines = noopAtCellEnd.splitlines(True) # keepends=True

      # use another variable, to evaluate with modifications without changing original
      modifiedCodeCellText = codeCellText + extraCodeLines
      if justSendNewlines:
         modifiedCodeCellText = ["\n","\n"] + extraCodeLines

      # loop through each line of code, evaluating it and saving the results
      output = []
      ignoreEmptyLines = interpreterSpec["ignoreEmptyLines"]
      if justSendNewlines: ignoreEmptyLines = False
      for codeLine in modifiedCodeCellText:
         #print("debug processing line:", [codeLine])
         interpResult = self.processPhysicalCodeLine(
               interpreterProcess, codeLine, ignoreEmptyLines=ignoreEmptyLines)
         #print("debug result of line:", [interpResult])
         output = output + interpResult # get the result, per line

      if len(output) > lyxNotebookUserSettings.maxLinesInOutputCell:
         output = output[:lyxNotebookUserSettings.maxLinesInOutputCell]
         output.append("<<< WARNING: Lines truncated by LyX Notebook. >>>""")

      if self.noEcho == False and interpreterSpec["promptAtCellEnd"]:
         output.append(interpreterProcess.mostRecentPrompt)

      codeCellText.evaluationOutput = output
      return output

   def updatePrompts(self, interpResult, interpreterProcess):
      """A utility function to update prompts across interpreter evaluation
      lines.  The argument interpResult is a list of lines resulting from
      an interpreter evaluation.  This routine prepends the most recently saved 
      prompt to the first command on the list, and saves the last line of the
      list as the new most recently saved prompt (to prepend next time).  Any 
      autoindenting after prompts is stripped off."""
      if len(interpResult) == 0: return
      interpResult[0] = interpreterProcess.mostRecentPrompt + interpResult[0]
      mostRecentPrompt = interpResult[-1]
      # remove any autoindent from mostRecentPrompt; note main and continuation 
      # prompts might have different lengths (though they usually do not)
      if mostRecentPrompt.find(interpreterProcess.spec["mainPrompt"]) == 0:
         interpreterProcess.mostRecentPrompt = interpreterProcess.spec["mainPrompt"]
         #print("debug replaced a main prompt")
      elif mostRecentPrompt.find(interpreterProcess.spec["contPrompt"]) == 0:
         interpreterProcess.mostRecentPrompt = interpreterProcess.spec["contPrompt"]
         #print("debug replaced a cont prompt")
      else: 
         print("Warning: prompt not recognized as main or continuation prompt.")
      return interpResult[0:-1]

   def processPhysicalCodeLine(self, interpreterProcess, codeLine, 
         ignoreEmptyLines = True):
      """Process the physical line of code codeLine in the interpreter with 
      index interpIndex.  Return a (possibly empty) list of all the result lines.
      The option ignoreEmptyLines ignores completely empty (all whitespace) lines,
      but not lines with comments."""

      # TODO, maybe convert any tabs to spaces in input lines

      interpSpec = interpreterProcess.spec
      indentCalc = interpreterProcess.indentCalc

      #print("\ndebug codeLine being processed is", codeLine.rstrip())

      # Ignore fully empty lines if ignoreEmptyLines, but not lines with comments, etc.
      # Python interpreter actually only ends indent blocks on zero-length lines, not
      # lines with only whitespace, but those might as well be ignored, too.
      if ignoreEmptyLines and len(codeLine.rstrip()) == 0:
         if not indentCalc.inStringLiteral():
            return []

      # update the indentation calculations for current physical line
      indentCalc.updateForPhysicalLine(codeLine)

      # send a completely empty line if the indentation level decreased to zero
      # (uses a recursive function call which does not ignoreEmptyLines)
      firstResults = []
      if interpSpec["indentDownToZeroNewline"] and indentCalc.indentLevelDownToZero():
         firstResults = self.processPhysicalCodeLine(interpreterProcess, "\n", 
               ignoreEmptyLines = False)

      # send the line of code to the interpreter
      interpreterProcess.externalInterp.write(codeLine) 

      # get the result of interpreting the line
      interpResult = interpreterProcess.externalInterp.read()
      interpResult = interpResult.splitlines(True) # keepends=True

      # if the final prompt was a main prompt, not continuation, reset indent counts
      if (len(interpResult) > 0 
            and interpResult[-1].rstrip() == interpSpec["mainPrompt"].rstrip()
            and interpResult[-1].find(interpSpec["mainPrompt"]) == 0):
         indentCalc.reset()

      # update the prompts (to remove final prompt and put prev prompt at beginning)
      interpResult = self.updatePrompts(interpResult, interpreterProcess)
      
      # if spec removeNewlineBeforePrompt is True and last line is empty, remove it
      if len(interpResult) > 0 and interpSpec["delNewlinePrePrompt"]:
         if interpResult[-1].strip() == "":
            interpResult = interpResult[:-1]

      # return the output, suppressing the first line if echo off
      # (note we're processing a physical line here, so the first line always
      # contains a prompt; even continued lines with no output have a prompt
      # line at the beginning)
      if self.noEcho and len(interpResult) > 0:
         return firstResults + interpResult[1:]
      else:
         return firstResults + interpResult
      
   def wrapLongLines(self, lineList):
      """A stub, which later can be used to do line-wrapping on long lines,
      or modified and renamed to do any sort of processing or formatting."""
      return lineList

   def displayPopupMessage(self, message, text=None, seconds=3):
      """Briefly display a message in a text window.  Will use a textbox if
      text is not None, otherwise a msgbox.  This is a kludge using a fork 
      to work around the limitations of EasyGUI.  BEWARE if an exit handler is 
      later added... killing child might kill the running interpreters.
      Works, but is not currently used; messages are sent to the Lyx status
      bar instead."""
      newpid = os.fork()
      if newpid == 0:
         # child displays text message until killed by parent
         if text==None:
            eg.msgbox(msg=message, title="LyX Notebook", ok_button="")
         else:
            eg.textbox(msg=message, title="LyX Notebook", text=text)
         sys.exit(0) # in case user closes window before kill
      else:
         time.sleep(seconds)
         os.kill(newpid,signal.SIGHUP)
      return

   def replaceCurrentBufferFile(self, newfile, reloadBuffer=True, messages=True):
      """Replace the current buffer file with the file newfile, saving
      a backup of the old file.  If reloadBuffer=True then the Lyx buffer is
      reloaded."""
      # write out buffer if it is unsaved, before copying to backup file
      self.lyxProcess.processLfun("buffer-write", warnERROR=False) 

      # get the basic data
      dirData = self.lyxProcess.getUpdatedLyxDirectoryData(autoSaveUpdate=False)
      numBackupBufferCopies = lyxNotebookUserSettings.numBackupBufferCopies

      # move the older save files down the list to make room
      for saveNum in range(numBackupBufferCopies-1,0,-1):
         older = ".LyxNotebookSave" + str(saveNum) + "_" + dirData[1]
         newer = ".LyxNotebookSave" + str(saveNum-1) + "_" + dirData[1]
         if os.path.exists(newer):
            if os.path.exists(older): os.remove(older)
            os.rename(newer, older)

      # wait for the buffer-write command started above to finish before final move
      prevMtime = 0
      while True:
         mtime = os.stat(os.path.join(dirData[0],dirData[1])).st_mtime
         if mtime > prevMtime: 
            # mtime only has 1-sec resolution, so must wait over a sec...
            # could use os.path.getmtime if OS supports greater (float) resolution
            # could also check if write returned error or account for the move 
            # times above to reduce the delay
            time.sleep(1.1) 
            prevMtime = mtime
         else: break

      # variable newer should have ended up at save file 0, so move buffer to that
      if os.path.exists(newer): os.remove(newer)
      os.rename(dirData[1], newer)
      os.rename(newfile, dirData[1])

      if reloadBuffer: self.reloadBufferFile()
      if messages: self.lyxProcess.showMessage(
            "Replaced current buffer with newly evaluated output cells.")
      return

   def reloadBufferFile(self, dontAskFirst=True):
      """Reload the current buffer file.  If dontAskFirst is True a method is used
      which simply does the reload without asking the user."""
      if dontAskFirst:
         # This command does not ask and always reloads:
         self.lyxProcess.processLfun("vc-command", 'R $$p "/bin/echo reloading..."')
         # TODO: Bug if we do not modify file and write it back out as below!  Why?
         # Cells are not read back in right, otherwise, until a save is done.
         self.lyxProcess.processLfun("command-sequence", 
               "self-insert x;char-delete-backward;buffer-write")
      else:
         # This LFUN will ask the user before reloading:
         self.lyxProcess.processLfun("buffer-reload")
      return

   def revertToMostRecentBatchEvalBackup(self, messages=False):
      """Revert the most recently saved batch backup file to be current buffer."""
      # get basic data, autosaving as last resort in case this makes things worse
      dirData = self.lyxProcess.getUpdatedLyxDirectoryData(autoSaveUpdate=True)
      numBackupBufferCopies = lyxNotebookUserSettings.numBackupBufferCopies

      mostRecentBackup =  ".LyxNotebookSave0_" + dirData[1]
      mostRecentBackupFull = os.path.join(dirData[0], mostRecentBackup)
      currentBufferFull = dirData[3]
      
      if not os.path.exists(mostRecentBackupFull):
         if messages:
            msg = "Error: No backup file to recover."
            choices = (["OK"])
            eg.buttonbox(msg, choices=choices)
            self.lyxProcess.showMessage(msg)
            print(msg)
         return

      backTime = time.ctime(os.stat(mostRecentBackupFull).st_mtime)
      bufferTime = time.ctime(os.stat(currentBufferFull).st_mtime)
      
      msg = "Are you sure you want to replace the current buffer with"
      msg += " the most recent backup?"
      msg += "\nBuffer's time is:\n   " + bufferTime
      msg += "\nBackup's time is:\n   " + backTime
      choices = (["Yes","No"])
      reply = eg.buttonbox(msg, choices=choices)
      if reply != "Yes": return

      os.remove(currentBufferFull)
      os.rename(mostRecentBackupFull, currentBufferFull)

      # shift down all the older backups
      for saveNum in range(1, numBackupBufferCopies):
         older = ".LyxNotebookSave" + str(saveNum) + "_" + dirData[1]
         newer = ".LyxNotebookSave" + str(saveNum-1) + "_" + dirData[1]
         if os.path.exists(older):
            if os.path.exists(newer): os.remove(newer)
            os.rename(older, newer)

      self.reloadBufferFile()
      if messages:
         msg = "Finished replacing current buffer with most recent batch backup"
         msg += " save file."
         self.lyxProcess.showMessage(msg)
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

