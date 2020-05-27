# ==================================================================================
#
# Scala
#
# ==================================================================================

from .spec_record import SpecRecord
from .python2_spec import *

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
    "startup_timeout_secs": 30, # startup can be slow...
    "read_output_timeout_secs": 30,
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


