# -*- coding: utf-8 -*-
"""
=========================================================================
This file is part of LyX Notebook, which works with LyX but is an
independent project.  License details (MIT) can be found in the file
COPYING.

Copyright (c) 2012 Allen Barker
=========================================================================

This file contains the specifications for all the interpreters which Lyx
Notebook is able to use.

To add a specification it is probably easiest to copy an existing one and then
change the names and the values.  The name for the spec itself (i.e., the
variable it is assigned to in the first line) should then be added to the list
`all_specs` at the end of this file.  All the fields must be present; there are
no default values.

We now briefly describe some of the fields.  See the python2 spec below for
descriptions of the others.

----

*  `prog_name` : An arbitrary descriptive string for the interpreter.  It is what
   will be printed out to describe the interpreter.  Uniqueness is not required.
   For example, by default Python 2 and Python 3 are both simply called Python.
   This string is used as the small label printed to the right of code cells.
   Changing this requires running install.py again.

*  `inset_specifier` : This is a string describing the interpreter which must be
   unique, and must contain only LETTER characters (no numbers).  This is
   because this string becomes part of the generated inset names, as well as a
   part of generated function names in Latex (Latex does not allow numbers in
   commands and \def strings).  Changing this requires running install.py again.

*  `listings_language` : the `"language=xxxxx"` setting for the Listings program.  It
   can be set to the empty string to use no predefined language formatting.
   Changing this requires running install.py again.

Changing any field other than one of the three above only requires restarting
Lyx Notebook.  The above three require `install.py` be run again to re-generate
the module files.

*  `run_command` : The command which is to be run; must be in `PATH` or a full pathname.

*  `run_arguments` : A list of arguments to the `run_command`.  Note that each part must
   be a separate element of the list.  For example, `["--rcfile", "/tmp/myRcFile"]`
   rather than putting the file with the flag part.

----

The `preambleLatexCode` string is initialization code which is substituted in the
preamble of the document for each module is loaded (each `interpreterSpec` is
placed in its own module).  If the same code is repeated for different modules
then be sure that it will not cause problems if it is run twice (such as when
two Lyx Notebook modules are loaded).

The big string blocks with Listings key=value pairs (such as
`python2.general_listings_code_format`) are Listings formatting code for all the
cells of the specified type.  These are substituted into the preamble template,
at places specified by metavars surrounded by `<< >>`.

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
import lyxNotebook_user_settings # in case any of these settings are needed
import os
import sys


class SpecRecord(object):

    """A class used as a data record for an interpreter specification.  All the
    data fields initialized to None should be assigned values."""

    def __init__(self):
        self.params = None # a dict mapping interpreter attributes to values
        self.preamble_latex_code = None # Latex init code to go in the preamble once.
        self.general_listings_code_format = None # format options for all code cells
        self.non_color_listings_code_format = None # format options for non-color code cells
        self.color_listings_code_format = None # format options for color code cells
        self.general_listings_output_format = None # format options for all output cells
        self.non_color_listings_output_format = None # format options for non-color output cells
        self.color_listings_output_format = None # format options for color output cells

all_specs = [] # the list of all defined specs; each section should append to it

#
# TODO: these language sections below could be separate files, in an interpreter_specs
# directory.  Then it is very easy to add a new interpreter, or modify one.  The
# bookkeeping is also simplified (someone could just send a file, not diffs).
# At the end, each should append to all_specs.
#

#
# ==================================================================================
#
# Python 2
#
# ==================================================================================

python2 = SpecRecord()
python2.params = {
    "prog_name": "Python",# name of the prog, used in formatted label
    "main_prompt": ">>> ",   # the main prompt
    "cont_prompt": "... ",   # the continuation prompt
    "run_command": "python", # command to run the interpreter, in path
    "run_arguments": ["-u"],   # arguments to the run_command
    "file_suffix": ".py",    # suffix for code in interpreter language
    "comment_line": "#",      # char which starts a comment line
    "line_continuation": "\\",     # char which denotes line continuation
    "inset_specifier": "PythonTwo", # e.g., Flex:LyxNotebook:Standard:PythonTwo
    "listings_language": "python", # the language=???? value for formatting
    "startup_sleep_secs": 0.01,     # initialization time for interpreter startup
    "before_read_sleep_secs": 0.01,     # delay between writing to interp and reading
    "noop_at_cell_end": "pass\n", # a command to always evaluate at cell ends
    "exit_command": "exit()\n", # the command to exit the interpreter
    "del_newline_pre_prompt": False,      # whether to remove a newline before prompt
    "prompt_at_cell_end": True,  # in echo mode, show waiting prompt at cell end
    "indent_down_to_zero_newline": True, # newline when Python indent goes down to zero
    "ignore_empty_lines": True,    # ignore lines of just whitespace in code cells
    "run_only_on_demand": True     # don't start unless required to eval a cell
}


# TODO: can this preamble code be generic, or might some interpreter want to change
# it?  All currently use it..... just define as generic and assign python to it
# like the others

# TODO: might prefer to have the frame command BEFORE the style command, so that
# users can reset the frames in their own local language styles (note comma issues
# should be automatically fixed now assuming no bugs)

python2.preamble_latex_code = r"""
   % Latex code for <<inset_specifier>> cells from interpreter_spec.py
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
   % Now define the Listings styles for Lyx Notebook <<inset_specifier>>,
   % setting the language to <<lst_language>> (which will be replaced by the
   % listings_language field of the general spec.  Note the default frame
   % conventions are defined here (since the general code format for Init
   % and Standard cells doesn't differ).
   %

   % define style lyxNotebookNoColorInit<<inset_specifier>>
   \lstdefinestyle{lyxNotebookNoColorInit<<inset_specifier>>}{
      language=<<lst_language>>,
      <<general_listings_code_format>>
      <<non_color_listings_code_format>>
      frame=TbLR
   }

   % define style lyxNotebookNoColorStandard<<inset_specifier>>
   \lstdefinestyle{lyxNotebookNoColorStandard<<inset_specifier>>}{
      style=lyxNotebookNoColorInit<<inset_specifier>>,
      frame=tblr
   }

   % define style lyxNotebookColorInit<<inset_specifier>>
   \lstdefinestyle{lyxNotebookColorInit<<inset_specifier>>}{
      language=<<lst_language>>,
      <<general_listings_code_format>>
      <<color_listings_code_format>>
      frame=TbLR
   }

   % define style lyxNotebookColorStandard<<inset_specifier>>
   \lstdefinestyle{lyxNotebookColorStandard<<inset_specifier>>}{
      style=lyxNotebookColorInit<<inset_specifier>>,
      frame=tblr
   }

   % define style lyxNotebookColorNonEval<<inset_specifier>>
   \lstdefinestyle{lyxNotebookColorNonEval<<inset_specifier>>}{
      style=lyxNotebookColorInit<<inset_specifier>>,
      frame=TBLR
   }

   % define style lyxNotebookNoColorNonEval<<inset_specifier>>
   \lstdefinestyle{lyxNotebookNoColorNonEval<<inset_specifier>>}{
      style=lyxNotebookNoColorInit<<inset_specifier>>,
      frame=TBLR
   }

   % define style lyxNotebookNoColorOutput<<inset_specifier>>
   \lstdefinestyle{lyxNotebookNoColorOutput<<inset_specifier>>}{
      language=,
      <<general_listings_output_format>>
      <<non_color_listings_output_format>>
      frame=tblr
   }

   % define lyxNotebookColorOutput<<inset_specifier>>
   \lstdefinestyle{lyxNotebookColorOutput<<inset_specifier>>}{
      language=,
      <<general_listings_output_format>>
      <<color_listings_output_format>>
      frame=tblr
   }

"""

# key=value pairs
# last in a list can end in comma or not, since this is checked-for and corrected,
# but should not end in a pure comment line (with nothing else but a comment)

python2.general_listings_code_format = r"""
      % general_listings_code_format
      showlines=true, % keep blank lines at end of listing blocks
      sensitive=true,
      morecomment=[s]{<<triple_quote>>}{<<triple_quote>>},
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

python2.non_color_listings_code_format = r"""
      % non_color_listings_code_format
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

python2.color_listings_code_format = r"""
      % color_listings_code_format
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

python2.general_listings_output_format = r"""
      % general_listings_output_format
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

python2.non_color_listings_output_format = r"""
      % non_color_listings_output_format
      % set the font to a gray color
      basicstyle=\lyxNotebookFontSize%
                 \setstretch{1}%
                 \lyxNotebookNoColorOutputFontFamily%
                 \color[rgb]{0.2,0.2,0.2}
"""

python2.color_listings_output_format = r"""
      % color_listings_output_format
      % set the font to a gray color
      basicstyle=\lyxNotebookFontSize%
                 \setstretch{1}
                 \lyxNotebookColorOutputFontFamily
                 \color[rgb]{0.2,0.2,0.2}
"""

all_specs.append(python2)

# ==================================================================================
#
# Python 3
#
# ==================================================================================
#
# This is the same as Python 2 except for prog_name, run_command, and inset_specifier.
# We could have just made python3 a deep copy of python2 and modified those values.

python3 = SpecRecord()
python3.params = {
    "prog_name": "Python", # name of the prog, used in formatted label
    "main_prompt": ">>> ",   # the main prompt
    "cont_prompt": "... ",   # the continuation prompt
    "run_command": "python3", # command to run the interpreter, in path
    "run_arguments": ["-u"],   # arguments to the run_command
    "file_suffix": ".py",    # suffix for code in interpreter language
    "comment_line": "#",      # char which starts a comment line
    "line_continuation": "\\",     # char which denotes line continuation
    "inset_specifier": "Python", # e.g., Flex:LyxNotebook:Standard:Python
    "listings_language": "python", # the language=???? value for formatting
    "startup_sleep_secs": 0.01,     # initialization time for interpreter startup
    "before_read_sleep_secs": 0.01,     # delay between writing to interp and reading
    "noop_at_cell_end": "pass\n", # a command to always evaluate at cell ends
    "exit_command": "exit()\n", # the command to exit the interpreter
    "del_newline_pre_prompt": False,      # whether to remove a newline before prompt
    "prompt_at_cell_end": True,  # in echo mode, show waiting prompt at cell end
    "indent_down_to_zero_newline": True, # newline when Python indent goes down to zero
    "ignore_empty_lines": True,    # ignore lines of just whitespace in code cells
    "run_only_on_demand": True     # don't start unless required to eval a cell
}

# all formatting is identical to Python2
python3.preamble_latex_code = python2.preamble_latex_code

python3.general_listings_code_format = python2.general_listings_code_format
python3.non_color_listings_code_format = python2.non_color_listings_code_format
python3.color_listings_code_format = python2.color_listings_code_format

python3.general_listings_output_format = python2.general_listings_output_format
python3.non_color_listings_output_format = python2.non_color_listings_output_format
python3.color_listings_output_format = python2.color_listings_output_format

all_specs.append(python3)

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
    "prog_name": "Sage",
    "main_prompt": "sage: ",
    "cont_prompt": "....: ",
    "run_command": "/usr/bin/sage", # try local, too
    "run_arguments": [],
    "file_suffix": ".sage",
    "comment_line": "#",
    "line_continuation": "\\",
    "inset_specifier": "Sage", # e.g., Flex:LyxNotebook:Standard:Sage
    "listings_language": "python", # same as Python
    "startup_sleep_secs": 3.0,  # sage startup is slow
    "before_read_sleep_secs": 0.02,  # sage slower than raw Python
    "noop_at_cell_end": "pass\npass\n", # two to catch some extra indent cases
    "exit_command": "exit()\n",
    "del_newline_pre_prompt": False,
    "prompt_at_cell_end": True,
    "indent_down_to_zero_newline": True,
    "ignore_empty_lines": True,
    "run_only_on_demand": True
}

# all formatting is identical to Python2
sage.preamble_latex_code = python2.preamble_latex_code

sage.general_listings_code_format = python2.general_listings_code_format
sage.non_color_listings_code_format = python2.non_color_listings_code_format
sage.color_listings_code_format = python2.color_listings_code_format

sage.general_listings_output_format = python2.general_listings_output_format
sage.non_color_listings_output_format = python2.non_color_listings_output_format
sage.color_listings_output_format = python2.color_listings_output_format

all_specs.append(sage)

# ==================================================================================
#
# Scala
#
# ==================================================================================

scala = SpecRecord()
scala.params = {
    "prog_name": "Scala",
    "main_prompt": "scala> ",
    "cont_prompt": "     | ",
    "run_command": "scala",
    "run_arguments": [],
    "file_suffix": ".scala",
    "comment_line": "//",
    "line_continuation": None,
    "inset_specifier": "Scala", # e.g., Flex:LyxNotebook:Standard:Scala
    "listings_language": "", # no Scala predefined yet in Listings
    "startup_sleep_secs": 1.0, # startup can be slow...
    "before_read_sleep_secs": 0.01,
    "noop_at_cell_end": None,
    "exit_command": "exit()\n",
    "del_newline_pre_prompt": True, # Scala interp. adds a blank line before prompt
    "prompt_at_cell_end": True,
    "indent_down_to_zero_newline": False,
    "ignore_empty_lines": True,
    "run_only_on_demand": True
}

scala.general_listings_code_format = r"""
      % general_listings_code_format
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
      morestring=[b]<<triple_quote>>,
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
scala.preamble_latex_code = python2.preamble_latex_code

# re-use the color settings from Python2
scala.non_color_listings_code_format = python2.non_color_listings_code_format
scala.color_listings_code_format = python2.color_listings_code_format

# use the same output cells as Python2
scala.general_listings_output_format = python2.general_listings_output_format
scala.non_color_listings_output_format = python2.non_color_listings_output_format
scala.color_listings_output_format = python2.color_listings_output_format

all_specs.append(scala)

# ==================================================================================
#
# R
#
# ==================================================================================

R = SpecRecord()
R.params = {
    "prog_name": "R",
    "main_prompt": "> ",
    "cont_prompt": "+ ",
    "run_command": "R",
    "run_arguments": ["--no-save", "--no-restore", "--no-readline"],
    "file_suffix": ".R",
    "comment_line": "#",
    "line_continuation": None,
    "inset_specifier": "R", # e.g., Flex:LyxNotebook:Standard:Scala
    "listings_language": "R", # no Scala predefined yet in Listings
    "startup_sleep_secs": 1.0,
    "before_read_sleep_secs": 0.01,
    "noop_at_cell_end": None,
    "exit_command": "quit(save=\"no\")\n",
    "del_newline_pre_prompt": False,
    "prompt_at_cell_end": True,
    "indent_down_to_zero_newline": False,
    "ignore_empty_lines": True,
    "run_only_on_demand": True
}

R.general_listings_code_format = r"""
      % general_listings_code_format
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
R.preamble_latex_code = python2.preamble_latex_code

# re-use the color settings from Python2
R.non_color_listings_code_format = python2.non_color_listings_code_format
R.color_listings_code_format = python2.color_listings_code_format

# use the same output cells as Python2
R.general_listings_output_format = python2.general_listings_output_format
R.non_color_listings_output_format = python2.non_color_listings_output_format
R.color_listings_output_format = python2.color_listings_output_format

all_specs.append(R)

# ==================================================================================
#
# Bash
#
# ==================================================================================

# Note that this interpreter is set-up to use a bashrc file provided in the directory
# auxiliaryFilesForInterpreters.  This bashrc file sources the usual ~/.bashrc
# (if it exists and is readable) but then redefines the prompt strings to the
# values which are set in the spec below.
bashrc_file = os.path.join(lyxNotebook_user_settings.lyx_notebook_source_dir,
                          "auxiliaryFilesForInterpreters", "lyxNotebookBashrc")

bash = SpecRecord()
bash.params = {
    "prog_name": "Bash",
    "main_prompt": "bash $ ",
    "cont_prompt": "bash > ",
    "run_command": "bash",
    "run_arguments": ["--rcfile", bashrc_file],
    "file_suffix": ".bash",
    "comment_line": "#",
    "line_continuation": None,
    "inset_specifier": "Bash", # e.g., Flex:LyxNotebook:Standard:Scala
    "listings_language": "bash", # no Scala predefined yet in Listings
    "startup_sleep_secs": 0.2,
    "before_read_sleep_secs": 0.01,
    "noop_at_cell_end": None,
    "exit_command": "exit\n",
    "del_newline_pre_prompt": False,
    "prompt_at_cell_end": True,
    "indent_down_to_zero_newline": False,
    "ignore_empty_lines": True,
    "run_only_on_demand": True
}

bash.general_listings_code_format = r"""
      % general_listings_code_format
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
bash.preamble_latex_code = python2.preamble_latex_code

# re-use the color settings from Python2
bash.non_color_listings_code_format = python2.non_color_listings_code_format
bash.color_listings_code_format = python2.color_listings_code_format

# use the same output cells as Python2
bash.general_listings_output_format = python2.general_listings_output_format
bash.non_color_listings_output_format = python2.non_color_listings_output_format
bash.color_listings_output_format = python2.color_listings_output_format

all_specs.append(bash)

# ==================================================================================
# end of spec definitions
# ==================================================================================

# Note we can remove anything from all_specs here (or, equivalently, comment-out
# the line above where it was added.

# ==================================================================================
# Make all the substitutions of the key=value pairs into the Latex preamble.
# ==================================================================================
# This could be done later with the subs in generateModuleFilesFromTemplateFiles.py,
# but we might as well build and check/test the full preamble here (a few metavars
# like <<lst_language>> and <<inset_specifier>> will remain to be substituted there).


def fix_comma(key_value_lines, end_in_comma=True):
    """Returns the key=value list with a trailing comma either there or not."""
    lines = key_value_lines.strip("\n\t ").splitlines() # kill begin and end empty lines
    if len(lines) == 0: return "% empty key-value list placeholder"
    # split off any comment at end of last line
    last_non_comment_line_index = -1
    for i in range(len(lines)-1, -1, -1):
        curr_line = lines[i].strip()
        if len(curr_line) == 0: continue
        if curr_line[0] != "%":
            last_non_comment_line_index = i
            break
    if last_non_comment_line_index == -1:
        return "\n".join(lines) # all lines are comments, re-join and return them
    last_line = lines[last_non_comment_line_index]
    i = 0; split_point = len(last_line)
    while i < len(last_line): # go through each char looking for comment part
        if last_line[i] == "\\":
            i += 2 # skip any escaped percent signs
            continue
        if last_line[i] == "%":
            split_point = i # found first non-escaped percent
            break
        i += 1
    main_last_line = last_line[0:split_point].rstrip()
    comment_last_line = last_line[split_point:]
    if main_last_line == "":
        print("Error: last line in interpreter spec key=value list cannot be comment.")
        sys.exit(-1)
    if main_last_line[-1] == ",":
        if not end_in_comma: main_last_line = main_last_line[0:-1]
    else:
        if end_in_comma: main_last_line = main_last_line + ","
    lines[last_non_comment_line_index] = main_last_line + " " + comment_last_line # rejoin
    return "\n".join(lines)

for spec in all_specs:
    preamble = spec.preamble_latex_code
    # make the metavar substitutions with replace
    preamble = preamble.replace("<<general_listings_code_format>>",
                                fix_comma(spec.general_listings_code_format, True))
    preamble = preamble.replace("<<non_color_listings_code_format>>",
                                fix_comma(spec.non_color_listings_code_format, True))
    preamble = preamble.replace("<<color_listings_code_format>>",
                                fix_comma(spec.color_listings_code_format, True))
    preamble = preamble.replace("<<general_listings_output_format>>",
                                fix_comma(spec.general_listings_output_format, True))
    preamble = preamble.replace("<<non_color_listings_output_format>>",
                                fix_comma(spec.non_color_listings_output_format, True))
    preamble = preamble.replace("<<color_listings_output_format>>",
                                fix_comma(spec.color_listings_output_format, True))
    spec.preamble_latex_code = preamble


if __name__ == "__main__":

    # look at the final, substituted version
    print(python2.preamble_latex_code)
