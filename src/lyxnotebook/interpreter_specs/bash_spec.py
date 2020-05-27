# ==================================================================================
#
# Bash
#
# ==================================================================================

import os
from .spec_record import SpecRecord
from .python2_spec import *
from ..config_file_processing import config_dict

# Note that this interpreter is set-up to use a bashrc file provided in the directory
# auxiliaryFilesForInterpreters.  This bashrc file sources the usual ~/.bashrc
# (if it exists and is readable) but then redefines the prompt strings to the
# values which are set in the spec below.
bashrc_file = os.path.join(config_dict["lyx_notebook_source_dir"],
                                          "default_config_file_and_data_files",
                                          "lyxNotebookBashrc.bash")

bash = SpecRecord()
bash.params = {
    "prog_name": "Bash",
    "main_prompt": "bash $ ",
    "cont_prompt": "bash > ",
    "run_command": "bash",
    "run_arguments": ["--rcfile", bashrc_file],
    "file_suffix": ".bash",
    "comment_line": "#",
    "line_continuation": "\\",
    "inset_specifier": "Bash", # e.g., Flex:LyxNotebook:Standard:Scala
    "listings_language": "bash",
    "startup_timeout_secs": 30,
    "read_output_timeout_secs": 30,
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

