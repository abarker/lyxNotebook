"""
=========================================================================
This file is part of LyX Notebook, which works with LyX but is an
independent project.  License details (MIT) can be found in the file
COPYING.

Copyright (c) 2012 Allen Barker
=========================================================================

This file processes the specifications for all the interpreters which Lyx
Notebook is able to use.  This file goes through each spec file, processing it
and then adding its `SpecRecord` instance to the list `all_specs`.  That list
is then imported and used by the module `generate_module_files_from_template`
to generate all the Lyx module files.

To add a specification it is probably easiest to copy an existing one and then
change the names and the values.  The name for the spec itself (i.e., the
variable it is assigned to in the first line) should then be added to the list
`all_specs` at the end of this file.  All the fields must be present; there are
no default values.

Some of the fields are briefly defined below.  See the python2 spec below for
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

import os
import sys
from ..config_file_processing import config_dict
from .spec_record import SpecRecord # TODO:  delete when all moved...

all_specs = [] # the list of all defined specs; each section should append to it

# TODO: Maybe loop over all files in dir???

from .python2_spec import python2
all_specs.append(python2)

from .python3_spec import python3
all_specs.append(python3)

from .sage_spec import sage
all_specs.append(sage)

from .scala_spec import scala
all_specs.append(scala)

from .r_spec import R
all_specs.append(R)

from .bash_spec import bash
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
    """Returns the key=value list (for Listings) with a trailing comma either
    there or not."""
    lines = key_value_lines.strip("\n\t ").splitlines() # kill begin and end empty lines
    if len(lines) == 0:
        return "% empty key-value list placeholder"
    # split off any comment at end of last line
    last_non_comment_line_index = -1
    for i in range(len(lines)-1, -1, -1):
        curr_line = lines[i].strip()
        if len(curr_line) == 0:
            continue
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
        if not end_in_comma:
            main_last_line = main_last_line[0:-1]
    else:
        if end_in_comma:
            main_last_line = main_last_line + ","
    lines[last_non_comment_line_index] = main_last_line + " " + comment_last_line # rejoin
    return "\n".join(lines)

def do_replacements(string, replacement_dict, fix_commas=True):
    """Return the string `string` with all the keys/meta-vars in it replaced
    by the corresponding values in `replacement_dict`.  The `fix_comma` function
    is also applied to the replacement text."""
    for key in replacement_dict:
        replacement_text = replacement_dict[key]
        if fix_commas:
            replacement_text = fix_comma(replacement_text, True)
        string = string.replace(key, replacement_text)
    return string

for spec in all_specs:
    preamble = spec.preamble_latex_code
    # make the metavar substitutions with replace
    replacement_dict = {
        "<<general_listings_code_format>>": spec.general_listings_code_format,
        "<<non_color_listings_code_format>>": spec.non_color_listings_code_format,
        "<<color_listings_code_format>>": spec.color_listings_code_format,
        "<<general_listings_output_format>>": spec.general_listings_output_format,
        "<<non_color_listings_output_format>>": spec.non_color_listings_output_format,
        "<<color_listings_output_format>>": spec.color_listings_output_format,
        }

    spec.preamble_latex_code = do_replacements(spec.preamble_latex_code, replacement_dict)

