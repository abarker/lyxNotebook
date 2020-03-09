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

from .spec_record import SpecRecord
from .python2_spec import *

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

