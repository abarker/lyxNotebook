# ==================================================================================
#
# Python 2
#
# ==================================================================================

from .spec_record import SpecRecord

python2 = SpecRecord()
python2.params = {
    "prog_name": "Python",# name of the prog, used in formatted label
    "main_prompt": ">>> ",   # the main prompt
    "cont_prompt": "... ",   # the continuation prompt
    "run_command": "python2", # command to run the interpreter, in path
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

