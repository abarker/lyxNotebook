# ==================================================================================
#
# Python 3
#
# ==================================================================================
#
# This is the same as Python 2 except for prog_name, run_command, and inset_specifier.
# We could have just made python3 a deep copy of python2 and modified those values.

from .spec_record import SpecRecord
from .python2_spec import *

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

