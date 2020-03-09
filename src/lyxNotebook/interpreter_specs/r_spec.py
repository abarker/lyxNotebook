# ==================================================================================
#
# R
#
# ==================================================================================

from .spec_record import SpecRecord
from .python2_spec import *

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
