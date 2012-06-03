"""
=========================================================================
This file is part of LyX Notebook, which works with LyX (and is licensed 
in the same way) but is an independent project.  License details (GPL V2) 
can be found in the file COPYING.

Copyright (C) 2012 Allen Barker
=========================================================================

This file contains the specifications for all the interpreters which Lyx
Notebook is able to use.

To add a specification it is probably easiest to copy an existing one and then
change the names and the values.  The name for the spec itself (i.e., the
variable it is assigned to in the first line) should then be added to the list
allSpecs at the end of this file.  All the fields must be present; there are no
default values.

We now briefly describe some of the fields.  See the python2 spec below for
descriptions of the others.

----

progName : An arbitrary descriptive string for the interpreter.  It is what
   will be printed out to describe the interpreter.  Uniqueness is not required.
   For example, by default Python 2 and Python 3 are both simply called Python.
   This string is used as the small label printed to the right of code cells.
   Changing this requires running setup.py again.

insetSpecifier : This is a string describing the interpreter which must be 
   unique, and must contain only LETTER characters (no numbers).  This is
   because this string becomes part of the generated inset names, as well as a
   part of generated function names in Latex (Latex does not allow numbers in
   commands and \def strings).  Changing this requires running setup.py again.  

listingsLanguage : the "language=xxxxx" setting for the Listings program.  It
   can be set to the empty string to use no predefined language formatting.
   Changing this requires running setup.py again.

Changing any field other than one of the three above only requires restarting
Lyx Notebook.  The above three require setup.py be run again to re-generate
the module files.

runCommand : The command which is to be run; must be in PATH or a full pathname.

runArguments : A list of arguments to the runCommand.  Note that each part must
   be a separate element of the list.  For example, ["--rcfile", "/tmp/myRcFile"]
   rather than putting the file with the flag part.

----

The preambleLatexCode string is initialization code which is substituted in the
preamble of the document for each module is loaded (each interpreterSpec is
placed in its own module).  If the same code is repeated for different modules
then be sure that it will not cause problems if it is run twice (such as when
two Lyx Notebook modules are loaded).

The big string blocks with Listings key=value pairs (such as
python2.generalListingsCodeFormat) are Listings formatting code for all the
cells of the specified type.  These are substituted into the preamble template,
at places specified by metavars surrounded by << >>.

The last line in such a block must not be a comment or end with a comment!
Otherwise, commas can either be present or not on the last line (the other
lines always need commas).  The lines should be indented the same as the
existing ones, in order to line up with nice formatting in the final, generated
files.  

Note that the color listings settings tend to be re-used from python2,
resulting in consistent color schemes for the different languages.

Note that the output formats tend to just be re-used from python2, and the
color and nonColor output formats are currently the same (color is not used
even in the color definitions).  We could have just had one type of output
cell, but at some point we might want different formatting for the output
of different interpreters.
"""

from __future__ import print_function, division
import lyxNotebookUserSettings # in case any of these settings are needed
import os

class SpecRecord(object):
   """A class used as a data record for an interpreter specification.  All the
   data fields initialized to None should be assigned values."""
   def __init__(self):
      params = None # a dict mapping interpreter attributes to values
      preambleLatexCode = None # Latex init code to go in the preamble once.
      generalListingsCodeFormat = None # format options for all code cells
      nonColorListingsCodeFormat = None # format options for non-color code cells
      colorListingsCodeFormat = None # format options for color code cells
      generalListingsOutputFormat = None # format options for all output cells
      nonColorListingsOutputFormat = None # format options for non-color output cells
      colorListingsOutputFormat = None # format options for color output cells

allSpecs = [] # the list of all defined specs; each section should append to it

#
# TODO: these language sections below could be separate files, in an interpreterSpecs
# directory.  Then it is very easy to add a new interpreter, or modify one.  The
# bookkeeping is also simplified (someone could just send a file, not diffs).
# At the end, each should append to allSpecs.
#

#
# ==================================================================================
#
# Python 2
#
# ==================================================================================

python2 = SpecRecord()
python2.params = {
      "progName"            :  "Python",# name of the prog, used in formatted label
      "mainPrompt"          :  ">>> ",   # the main prompt
      "contPrompt"          :  "... ",   # the continuation prompt
      "runCommand"          :  "python", # command to run the interpreter, in path
      "runArguments"        :  ["-u"],   # arguments to the runCommand
      "fileSuffix"          :  ".py",    # suffix for code in interpreter language
      "commentLine"         :  "#",      # char which starts a comment line
      "lineContinuation"    :  "\\",     # char which denotes line continuation
      "insetSpecifier"      :  "PythonTwo", # e.g., Flex:LyxNotebook:Standard:PythonTwo
      "listingsLanguage"    :  "python", # the language=???? value for formatting
      "startupSleepSecs"    :  0.01,     # initialization time for interpreter startup
      "beforeReadSleepSecs" :  0.01,     # delay between writing to interp and reading
      "noopAtCellEnd"       :  "pass\n", # a command to always evaluate at cell ends
      "exitCommand"         :  "exit()\n", # the command to exit the interpreter
      "delNewlinePrePrompt" :  False,      # whether to remove a newline before prompt
      "promptAtCellEnd"     :  True,  # in echo mode, show waiting prompt at cell end
      "indentDownToZeroNewline" : True, # newline when Python indent goes down to zero
      "ignoreEmptyLines"    :  True,    # ignore lines of just whitespace in code cells
      "runOnlyOnDemand"     :  True     # don't start unless required to eval a cell 
      }


python2.preambleLatexCode= r"""
   % Latex code for <<insetSpecifier>> cells from interpreterSpec.py
   %
   % Define some of the variables described in the documentation to set the font
   % size and family.  These definitions should preferably be used below instead of
   % the values themselves (so users can easily redefine these default values
   % from their preamble).
   \def\lyxNotebookFontSize{\footnotesize}
   \def\lyxNotebookColorCodeFontFamily{\ttfamily}
   \def\lyxNotebookColorOutputFontFamily{\ttfamily}
   \def\lyxNotebookNoColorCodeFontFamily{\sffamily}
   \def\lyxNotebookNoColorOutputFontFamily{\sffamily}
   \def\lyxNotebookLabelFormat{\ttfamily\tiny\bfseries}
   
   % define some colors to use
   \definecolor{gray9}{gray}{0.5}
   \definecolor{darkGray9}{gray}{0.05} % almost black, for normal text with colors
   \definecolor{green9}{rgb}{0,0.6,0}
   \definecolor{darkerGreen9}{rgb}{0,0.3,0}
   \definecolor{darkerRed9}{rgb}{0.6,0.0,0.0}
   \definecolor{brightRed9}{rgb}{1.0,0.0,0.0}
   \definecolor{yellowGold9}{rgb}{0.7,0.5,0.0}
   \definecolor{blue9}{rgb}{0.20,0.20,1.0}
   \definecolor{darkerBlue9}{rgb}{0.20,0.20,0.60}
   \definecolor{pinkRed9}{rgb}{0.9,0.2,0.4}
   \definecolor{turquoise9}{rgb}{0.0,0.6,1.0}
   \definecolor{bluishPurple9}{rgb}{0.2,0.0,1.0}
   \definecolor{purple9}{rgb}{0.4,0.0,1.0}
   
   %
   % Now define the Listings styles for Lyx Notebook <<insetSpecifier>>,
   % setting the language to <<lstLanguage>> (which will be replaced by the 
   % listingsLanguage field of the general spec.  Note the default frame
   % conventions are defined here (since the general code format for Init
   % and Standard cells doesn't differ).
   %

   % define style lyxNotebookNoColorInit<<insetSpecifier>>
   \lstdefinestyle{lyxNotebookNoColorInit<<insetSpecifier>>}{
      language=<<lstLanguage>>,
      <<generalListingsCodeFormat>>
      <<nonColorListingsCodeFormat>>
      frame=TbLR
   }

   % define style lyxNotebookNoColorStandard<<insetSpecifier>>
   \lstdefinestyle{lyxNotebookNoColorStandard<<insetSpecifier>>}{
      style=lyxNotebookNoColorInit<<insetSpecifier>>,
      frame=tblr
   }

   % define style lyxNotebookColorInit<<insetSpecifier>>
   \lstdefinestyle{lyxNotebookColorInit<<insetSpecifier>>}{
      language=<<lstLanguage>>,
      <<generalListingsCodeFormat>>
      <<colorListingsCodeFormat>>
      frame=TbLR
   }

   % define style lyxNotebookColorStandard<<insetSpecifier>>
   \lstdefinestyle{lyxNotebookColorStandard<<insetSpecifier>>}{
      style=lyxNotebookColorInit<<insetSpecifier>>,
      frame=tblr
   }

   % define style lyxNotebookColorNonEval<<insetSpecifier>>
   \lstdefinestyle{lyxNotebookColorNonEval<<insetSpecifier>>}{
      style=lyxNotebookColorInit<<insetSpecifier>>,
      frame=TBLR
   }

   % define style lyxNotebookNoColorNonEval<<insetSpecifier>>
   \lstdefinestyle{lyxNotebookNoColorNonEval<<insetSpecifier>>}{
      style=lyxNotebookNoColorInit<<insetSpecifier>>,
      frame=TBLR
   }

   % define style lyxNotebookNoColorOutput<<insetSpecifier>>
   \lstdefinestyle{lyxNotebookNoColorOutput<<insetSpecifier>>}{
      language=,
      <<generalListingsOutputFormat>>
      <<nonColorListingsOutputFormat>>
      frame=tblr
   }

   % define lyxNotebookColorOutput<<insetSpecifier>>
   \lstdefinestyle{lyxNotebookColorOutput<<insetSpecifier>>}{
      language=,
      <<generalListingsOutputFormat>>
      <<colorListingsOutputFormat>>
      frame=tblr
   }

"""

#
# key=value pairs
# last a list can end in comma or not, but cannot end in comment
# --> with comma on all they can be rearranged more easily without errors
#     (except beware comments at end! not checked for at all)

python2.generalListingsCodeFormat = r"""
      % generalListingsCodeFormat
      showlines=true, % keep blank lines at end of listing blocks
      sensitive=true,
      morecomment=[s]{<<tripleQuote>>}{<<tripleQuote>>},
      %alsoletter={1234567890}, % numbers like letters
      % but in otherkeywords causes it to highlight in strings and comments
      %otherkeywords={(,),[,],\{,\},@,\,,:,.,`,=,;,+=,-=,*=,/=,//=,%=,&=,|=,^=,>>=,<<=,**=} % delimiters in Python
      %otherkeywords={1,2,3,4,5,6,7,8,9,0,-,=,+,[,],(,),\{,\},:,*,!},
      %
      % The keywords need to be redefined to reset the "import" color.
      % See http://docs.python.org/reference/lexical_analysis.html
      keywords=[1]{and,as,assert,break,class,continue,def,del,elif,else,%
                   except,exec,finally,for,global,if,in,is,lambda,not,or,%
                   pass,print,raise,return,try,while,with,yield},
      morekeywords=[2]{True, False, None, self, NotImplemented, Ellipsis,%
                       __debug__, quit, exit, copyright, license, credits},
      morekeywords=[3]{from,import}, % note "as" is also in "with" and "except"
      %mathescape=true,
      % Linebreak symbols: arrows look nice but mess up the frame
      % prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},
      % postbreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\diagdown}},
      % Use backslash instead:
      prebreak=\bf\textbackslash,
      showstringspaces=false,
      breaklines=true,
      breakatwhitespace=true,
      breakindent=1.5em, 
      breakautoindent=true,
      % fancyvrb=true, % causes problems, even with all but lang commented out
      % numbers=left, numberstyle=\tiny, stepnumber=1, numbersep=6pt,
      % columns=flexible,
      % columns=fullflexible, % good with monospace font, & more chars per line
      columns=fixed, % fewer chars per line, but keeps extra spaces inserted
      % linewidth=\linewidth, % default seems to work better
      upquote=true,
"""

python2.nonColorListingsCodeFormat = r"""
      % nonColorListingsCodeFormat
      basicstyle=\lyxNotebookFontSize%
                 \setstretch{1}%
                 \lyxNotebookNoColorCodeFontFamily%
                 \color{darkGray9}, 
      stringstyle=\ttfamily, % use ttfamily for strings at least
      %commentstyle=\upshape, % don't use the default italic comments
      commentstyle=\slshape\color[rgb]{0.3,0.3,0.3}, % slanted gray
      %commentstyle=\itshape,
      keywordstyle=[1]\bfseries, 
      keywordstyle=[2]\bfseries,
      keywordstyle=[3]\bfseries,
"""

python2.colorListingsCodeFormat = r"""
      % colorListingsCodeFormat
      basicstyle=\lyxNotebookFontSize%
                 \setstretch{1}%
                 \lyxNotebookColorCodeFontFamily%
                 \color{darkGray9}, 
      rulecolor=\color{black}, % may be needed for line-broken color lines
      %identifierstyle=\color{darkGray9},
      stringstyle=\ttfamily\color{blue9},
      %stringstyle=\ttfamily\color{darkerBlue9},
      %stringstyle=\ttfamily\color{green9},
      %commentstyle=\upshape\color{green9},
      %commentstyle=\slshape\color{darkerGreen9},
      commentstyle=\slshape\color[rgb]{0.0,0.4,0.0},
      keywordstyle=[1]\bfseries\color{darkerRed9}, 
      keywordstyle=[2]\bfseries\color{pinkRed9},
      keywordstyle=[3]\bfseries\color{yellowGold9},
"""

python2.generalListingsOutputFormat = r"""
      % generalListingsOutputFormat
      showlines=true, % keep blank lines at end
      %mathescape=true,
      showstringspaces=false,
      breaklines=true,
      breakatwhitespace=true,
      breakindent=1.5em, breakautoindent=true,
      % Linebreaks: see comments earlier for code cells; arrows mess up frames.
      % prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},
      % postbreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\diagdown}},
      % Use backslash instead.
      prebreak=\bf\textbackslash,
      % linewidth=\linewidth, % default seems to work better
      % numbers=left, numberstyle=\tiny, stepnumber=1, numbersep=6pt,
      % columns=flexible, % 
      % columns=fullflexible, % good with monospace font, & more chars per line
      columns=fixed, % fewer chars per line, but keeps extra spaces inserted
      aboveskip=\doubleskipamount, % make abut the cell above, a calulated value
      upquote=true,
"""

python2.nonColorListingsOutputFormat = r"""
      % nonColorListingsOutputFormat
      % set the font to a gray color
      basicstyle=\lyxNotebookFontSize%
                 \setstretch{1}%
                 \lyxNotebookNoColorOutputFontFamily%
                 \color[rgb]{0.2,0.2,0.2}
"""

python2.colorListingsOutputFormat = r"""
      % colorListingsOutputFormat
      % set the font to a gray color
      basicstyle=\lyxNotebookFontSize%
                 \setstretch{1}
                 \lyxNotebookColorOutputFontFamily
                 \color[rgb]{0.2,0.2,0.2}
"""

allSpecs.append(python2)

# ==================================================================================
#
# Python 3
#
# ==================================================================================
#
# This is the same as Python 2 except for progName, runCommand, and insetSpecifier.
# We could have just made python3 a deep copy of python2 and modified those values.

python3 = SpecRecord()
python3.params = {
      "progName"            :  "Python", # name of the prog, used in formatted label
      "mainPrompt"          :  ">>> ",   # the main prompt
      "contPrompt"          :  "... ",   # the continuation prompt
      "runCommand"          :  "python3", # command to run the interpreter, in path
      "runArguments"        :  ["-u"],   # arguments to the runCommand
      "fileSuffix"          :  ".py",    # suffix for code in interpreter language
      "commentLine"         :  "#",      # char which starts a comment line
      "lineContinuation"    :  "\\",     # char which denotes line continuation
      "insetSpecifier"      :  "Python", # e.g., Flex:LyxNotebook:Standard:Python
      "listingsLanguage"    :  "python", # the language=???? value for formatting
      "startupSleepSecs"    :  0.01,     # initialization time for interpreter startup
      "beforeReadSleepSecs" :  0.01,     # delay between writing to interp and reading
      "noopAtCellEnd"       :  "pass\n", # a command to always evaluate at cell ends
      "exitCommand"         :  "exit()\n", # the command to exit the interpreter
      "delNewlinePrePrompt" :  False,      # whether to remove a newline before prompt
      "promptAtCellEnd"     :  True,  # in echo mode, show waiting prompt at cell end
      "indentDownToZeroNewline" : True, # newline when Python indent goes down to zero
      "ignoreEmptyLines"    :  True,    # ignore lines of just whitespace in code cells
      "runOnlyOnDemand"     :  True     # don't start unless required to eval a cell 
      }

# all formatting is identical to Python2
python3.preambleLatexCode = python2.preambleLatexCode

python3.generalListingsCodeFormat = python2.generalListingsCodeFormat
python3.nonColorListingsCodeFormat = python2.nonColorListingsCodeFormat
python3.colorListingsCodeFormat = python2.colorListingsCodeFormat

python3.generalListingsOutputFormat = python2.generalListingsOutputFormat
python3.nonColorListingsOutputFormat = python2.nonColorListingsOutputFormat
python3.colorListingsOutputFormat = python2.colorListingsOutputFormat

allSpecs.append(python3)

# ==================================================================================
#
# Sage
#
# ==================================================================================
#
# The Sage spec is almost the same as Python.  One difference
# is that two pass commands are issued after each cell (rather than just one).
# This is so that the following cell example will 1) catch the error, and 2)
# return to the Sage main prompt.
#
#   if 4==4:
#      for i in [1,2]:
#
#         print "x"
#

sage = SpecRecord()
sage.params = {
      "progName"            :  "Sage",
      "mainPrompt"          :  "sage: ",
      "contPrompt"          :  "....: ",
      "runCommand"          :  "/home/nobackup/sage/sage-4.8/sage", # try local, too
      "runArguments"        :  [],
      "fileSuffix"          :  ".sage",
      "commentLine"         :  "#",
      "lineContinuation"    :  "\\",
      "insetSpecifier"      :  "Sage", # e.g., Flex:LyxNotebook:Standard:Sage
      "listingsLanguage"    :  "python", # same as Python
      "startupSleepSecs"    :  1.0,  # sage startup is slow
      "beforeReadSleepSecs" :  0.02,  # sage slower than raw Python
      "noopAtCellEnd"       :  "pass\npass\n", # two to catch some extra indent cases
      "exitCommand"         :  "exit()\n",
      "delNewlinePrePrompt" :  False,
      "promptAtCellEnd"     :  True,
      "indentDownToZeroNewline" : True,
      "ignoreEmptyLines"    :  True,
      "runOnlyOnDemand"     :  True
      }

# all formatting is identical to Python2
sage.preambleLatexCode = python2.preambleLatexCode

sage.generalListingsCodeFormat = python2.generalListingsCodeFormat
sage.nonColorListingsCodeFormat = python2.nonColorListingsCodeFormat
sage.colorListingsCodeFormat = python2.colorListingsCodeFormat

sage.generalListingsOutputFormat = python2.generalListingsOutputFormat
sage.nonColorListingsOutputFormat = python2.nonColorListingsOutputFormat
sage.colorListingsOutputFormat = python2.colorListingsOutputFormat

allSpecs.append(sage)

# ==================================================================================
#
# Scala
#
# ==================================================================================

scala = SpecRecord()
scala.params = {
      "progName"            :  "Scala",
      "mainPrompt"          :  "scala> ",
      "contPrompt"          :  "     | ",
      "runCommand"          :  "scala",
      "runArguments"        :  [],
      "fileSuffix"          :  ".scala",
      "commentLine"         :  "//",
      "lineContinuation"    :  None,
      "insetSpecifier"      :  "Scala", # e.g., Flex:LyxNotebook:Standard:Scala
      "listingsLanguage"    :  "", # no Scala predefined yet in Listings
      "startupSleepSecs"    :  1.0, # startup can be slow...
      "beforeReadSleepSecs" :  0.01,
      "noopAtCellEnd"       :  None,
      "exitCommand"         :  "exit()\n",
      "delNewlinePrePrompt" :  True, # Scala interp. adds a blank line before prompt
      "promptAtCellEnd"     :  True, 
      "indentDownToZeroNewline" : False,
      "ignoreEmptyLines"    :  True,
      "runOnlyOnDemand"     :  True
      }

scala.generalListingsCodeFormat = r"""
      % generalListingsCodeFormat
      showlines=true, % keep blank lines at end of listing blocks
      sensitive=true,
      morekeywords={abstract,case,catch,class,def,%
         do,else,extends,false,final,finally,%
         for,if,implicit,import,match,mixin,%
         new,null,object,override,package,%
         private,protected,requires,return,sealed,%
         super,this,throw,trait,true,try,%
         type,val,var,while,with,yield},
      %otherkeywords={=>,<-,<\%,<:,>:,\#,@},
      morecomment=[l]{//},
      morecomment=[n]{/*}{*/},
      morestring=[b]",
      morestring=[b]',
      morestring=[b]<<tripleQuote>>,
      %mathescape=true,
      % Use backslash for line continuation.
      prebreak=\bf\textbackslash,
      showstringspaces=false,
      breaklines=true,
      breakatwhitespace=true,
      breakindent=1.5em, 
      breakautoindent=true,
      % numbers=left, numberstyle=\tiny, stepnumber=1, numbersep=6pt,
      % columns=flexible, % 
      % columns=fullflexible, % good with monospace font, & more chars per line
      columns=fixed, % fewer chars per line, but keeps extra spaces inserted
      linewidth=\linewidth, % same right margin in indented env., boxes smaller
      upquote=true,
"""

# use same code in the preamble
scala.preambleLatexCode = python2.preambleLatexCode

# re-use the color settings from Python2
scala.nonColorListingsCodeFormat = python2.nonColorListingsCodeFormat
scala.colorListingsCodeFormat = python2.colorListingsCodeFormat

# use the same output cells as Python2
scala.generalListingsOutputFormat = python2.generalListingsOutputFormat
scala.nonColorListingsOutputFormat = python2.nonColorListingsOutputFormat
scala.colorListingsOutputFormat = python2.colorListingsOutputFormat

allSpecs.append(scala)

# ==================================================================================
#
# R
#
# ==================================================================================

R = SpecRecord()
R.params = {
      "progName"            :  "R",
      "mainPrompt"          :  "> ",
      "contPrompt"          :  "+ ",
      "runCommand"          :  "R",
      "runArguments"        :  ["--no-save", "--no-restore", "--no-readline"],
      "fileSuffix"          :  ".R",
      "commentLine"         :  "#",
      "lineContinuation"    :  None,
      "insetSpecifier"      :  "R", # e.g., Flex:LyxNotebook:Standard:Scala
      "listingsLanguage"    :  "R", # no Scala predefined yet in Listings
      "startupSleepSecs"    :  1.0,
      "beforeReadSleepSecs" :  0.01,
      "noopAtCellEnd"       :  None,
      "exitCommand"         :  "quit(save=\"no\")\n",
      "delNewlinePrePrompt" :  False, 
      "promptAtCellEnd"     :  True, 
      "indentDownToZeroNewline" : False,
      "ignoreEmptyLines"    :  True,
      "runOnlyOnDemand"     :  True
      }

R.generalListingsCodeFormat= r"""
      % generalListingsCodeFormat
      showlines=true, % keep blank lines at end of listing blocks
      sensitive=true,
      upquote=true,
      %mathescape=true,
      % Use backslash for line continuation.
      prebreak=\bf\textbackslash,
      showstringspaces=false,
      % numbers=left, numberstyle=\tiny, stepnumber=1, numbersep=6pt,
      % columns=flexible, % 
      % columns=fullflexible, % good with monospace font, & more chars per line
      columns=fixed, % fewer chars per line, but keeps extra spaces inserted
      linewidth=\linewidth, % boxes smaller, same right margin in indented env.
      breaklines=true,
      breakatwhitespace=true,
      breakindent=1.5em, 
      breakautoindent=true,
"""

# use same code in the preamble
R.preambleLatexCode = python2.preambleLatexCode

# re-use the color settings from Python2
R.nonColorListingsCodeFormat = python2.nonColorListingsCodeFormat
R.colorListingsCodeFormat = python2.colorListingsCodeFormat

# use the same output cells as Python2
R.generalListingsOutputFormat = python2.generalListingsOutputFormat
R.nonColorListingsOutputFormat = python2.nonColorListingsOutputFormat
R.colorListingsOutputFormat = python2.colorListingsOutputFormat

allSpecs.append(R)

# ==================================================================================
#
# Bash
#
# ==================================================================================

# Note that this interpreter is set-up to use a bashrc file provided in the directory
# auxiliaryFilesForInterpreters.  This bashrc file sources the usual ~/.bashrc
# (if it exists and is readable) but then redefines the prompt strings to the
# values which are set in the spec below.
bashrcFile = os.path.join(lyxNotebookUserSettings.lyxNotebookSourceDir, 
      "auxiliaryFilesForInterpreters", "lyxNotebookBashrc")

bash = SpecRecord()
bash.params = {
      "progName"            :  "Bash",
      "mainPrompt"          :  "bash $ ",
      "contPrompt"          :  "bash > ",
      "runCommand"          :  "bash",
      "runArguments"        :  ["--rcfile", bashrcFile], 
      "fileSuffix"          :  ".bash",
      "commentLine"         :  "#",
      "lineContinuation"    :  None,
      "insetSpecifier"      :  "Bash", # e.g., Flex:LyxNotebook:Standard:Scala
      "listingsLanguage"    :  "bash", # no Scala predefined yet in Listings
      "startupSleepSecs"    :  0.2,
      "beforeReadSleepSecs" :  0.01,
      "noopAtCellEnd"       :  None,
      "exitCommand"         :  "exit\n",
      "delNewlinePrePrompt" :  False, 
      "promptAtCellEnd"     :  True, 
      "indentDownToZeroNewline" : False,
      "ignoreEmptyLines"    :  True,
      "runOnlyOnDemand"     :  True
      }

bash.generalListingsCodeFormat= r"""
      % generalListingsCodeFormat
      showlines=true, % keep blank lines at end of listing blocks
      sensitive=true,
      upquote=true,
      %mathescape=true,
      % Use backslash for line continuation.
      prebreak=\bf\textbackslash,
      showstringspaces=false,
      % numbers=left, numberstyle=\tiny, stepnumber=1, numbersep=6pt,
      % columns=flexible, % 
      % columns=fullflexible, % good with monospace font, & more chars per line
      columns=fixed, % fewer chars per line, but keeps extra spaces inserted
      linewidth=\linewidth, % boxes smaller, same right margin in indented env.
      breaklines=true,
      breakatwhitespace=true,
      breakindent=1.5em, 
      breakautoindent=true,
"""

# use same code in the preamble
bash.preambleLatexCode = python2.preambleLatexCode

# re-use the color settings from Python2
bash.nonColorListingsCodeFormat = python2.nonColorListingsCodeFormat
bash.colorListingsCodeFormat = python2.colorListingsCodeFormat

# use the same output cells as Python2
bash.generalListingsOutputFormat = python2.generalListingsOutputFormat
bash.nonColorListingsOutputFormat = python2.nonColorListingsOutputFormat
bash.colorListingsOutputFormat = python2.colorListingsOutputFormat

allSpecs.append(bash)

# ==================================================================================
# end of spec definitions
# ==================================================================================   

# Note we can remove anything from allSpecs here (or, equivalently, comment-out 
# the line above where it was added.

# ==================================================================================
# Make all the substitutions of the key=value pairs into the Latex preamble.
# ==================================================================================
# This could be done later with the subs in generateModuleFilesFromTemplateFiles.py,
# but we might as well build and check/test the full preamble here (a few metavars 
# like <<lstLanguage>> and <<insetSpecifier>> will remain to be substituted there).

def fixComma(keyValueLines, endInComma=True):
   """Returns the key=value list with a trailing comma either there or not."""
   lines = keyValueLines.splitlines()
   linesNoEmpty = [ line.rstrip() for line in lines ]
   if len(linesNoEmpty)==0: return "% empty key-value list placeholder"
   if linesNoEmpty[-1][-1] == ",":
      if not endInComma: linesNoEmpty[-1] = linesNoEmpty[-1][0:-1]
   else:
      if endInComma: linesNoEmpty[-1] = linesNoEmpty[-1] + ","
   return "\n".join(linesNoEmpty).strip("\n\t ") # kill begin and end whitespace

for spec in allSpecs:
   preamble = spec.preambleLatexCode
   preamble = preamble.replace("<<generalListingsCodeFormat>>", 
                               fixComma(spec.generalListingsCodeFormat,True))
   preamble = preamble.replace("<<nonColorListingsCodeFormat>>",
                               fixComma(spec.nonColorListingsCodeFormat,True))
   preamble = preamble.replace("<<colorListingsCodeFormat>>",
                               fixComma(spec.colorListingsCodeFormat,True))
   preamble = preamble.replace("<<generalListingsOutputFormat>>",
                               fixComma(spec.generalListingsOutputFormat,True))
   preamble = preamble.replace("<<nonColorListingsOutputFormat>>",
                               fixComma(spec.nonColorListingsOutputFormat,True))
   preamble = preamble.replace("<<colorListingsOutputFormat>>",
                               fixComma(spec.colorListingsOutputFormat,True))
   spec.preambleLatexCode = preamble


if __name__ == "__main__":

   # look at the final, substituted version
   print(python2.preambleLatexCode)

