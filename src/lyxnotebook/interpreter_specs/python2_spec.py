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


