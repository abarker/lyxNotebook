"""

=========================================================================
This file is part of LyX Notebook, which works with LyX but is an
independent project.  License details (MIT) can be found in the file
COPYING.

Copyright (c) 2012 Allen Barker
=========================================================================

Generate all the `.module` files from templates.  The function
`generate_files_from_templates` performs the operations.

This module is only used by `install.py` to generate `.module` files.

"""

import sys
import os

# The interpreterSpecs module is loaded because it contains the string defining
# the Listings formatting language for each type of interpreter it defines.
from .process_interpreter_specs import all_specs
from ..config_file_processing import config_dict

# =============================================================
# Define the basic template for the header of the .module file.
# There is 1) a common beginning part in each module, 2) a part
# which is looped over <<basic_cell_type>>, 3) and a closing section.
# =============================================================

# All the Lyx modules for cells share this common header.
module_header_template_common = \
    r"""#\DeclareLyXModule{Lyx Notebook <<inset_specifier>>}
#DescriptionBegin
#The <<inset_specifier>> cells for Lyx Notebook.
#DescriptionEnd

# Author : alb
#
# THIS FILE IS AUTOMATICALLY GENERATED BY generateModuleFilesFromTemplate.py
# Modifications can be made, but they will be overwritten if it is run again.

#Format 21
Format 66
#Format 80

Requires "listings,verbatim,ifthen,color,marginnote,needspace,graphicx,setspace,textcomp"

AddToPreamble
   %
   % The preamble inserted by the Lyx Notebook module for <<inset_specifier>>.
   %
   \usepackage{listings}
   \usepackage{verbatim} % to make comment blocks for non-printing
   \usepackage{ifthen} % etoolbox is apparently more modern, but ifthen works fine
   \usepackage{color}
   \usepackage{marginnote} % for small labels to right of cells
   \usepackage{needspace} % prevent bad line breaks hopefully
   \usepackage{graphicx} % to rotate the small labels to the right of cells
   \usepackage{setspace} % needed for \setstretch, which may not be needed
   % \usepackage[T1]{fontenc} % needed for some fonts if not already loaded
   \usepackage{textcomp} % needed for upquote=true option and fonts like beramono
   % \usepackage{courier} % for lack of bold in Computer Modern typewriter font
   % \usepackage{palatino}
   %
   % Just tell users in docs to select luximono or beramono for tt font, from
   % lyx document menu, if they have it installed.
   %\IfFileExists{luximono.sty}{
   %   \usepackage[scaled]{luximono} % recommended by some, not preloaded
   %}
   %{}
   % \usepackage[scaled]{beramono} % bitstream vera mono
   % \usepackage[scaled]{inconsolata}

   % set some global formatting options to their default values
   \def\lyxNotebookNoColor{false} % use color unless this def is overridden
   \def\lyxNotebookNoCellLabels{false} % put small label on cells unless set true
   \def\lyxNotebookNeedspaceLabelValue{4\baselineskip}

"""

# This part of the header for modules contains meta-vars which depend on the spec.
# It is looped over all basic cell types (Init, Standard, Output) replacing the
# meta-vars and appending to the bottom of the part just above.
module_header_template_basic_cell_type_dependent = \
    r"""
   %
   % Header stuff for the <<inset_specifier>> <<basic_cell_type>> cells.
   %
   % Define the function to turn off printing (just make same as verbatim comment)
   % for the inset specifier <<inset_specifier>> and basic cell type <<basic_cell_type>>
   % Note at least some EOL comments required below or extra space inserted in text.
   \def\lyxNotebookPrintingIsOff<<basic_cell_type>><<inset_specifier>>{false}
   \def\lyxNotebookPrintOff<<basic_cell_type>><<inset_specifier>>{%
      \def\lyxNotebookPrintingIsOff<<basic_cell_type>><<inset_specifier>>{true}%
      \let\oldLyxNotebookCell<<basic_cell_type>><<inset_specifier>>\lyxNotebookCell<<basic_cell_type>><<inset_specifier>>%
      \let\lyxNotebookCell<<basic_cell_type>><<inset_specifier>>=\comment%
      \let\oldEndlyxNotebookCell<<basic_cell_type>><<inset_specifier>>\endlyxNotebookCell<<basic_cell_type>><<inset_specifier>>%
      \let\endlyxNotebookCell<<basic_cell_type>><<inset_specifier>>=\endcomment%
   }%

   % Define the function to turn printing back on if it has been turned off
   % for the inset specifier <<inset_specifier>> and basic cell type <<basic_cell_type>>
   % Note at least some EOL comments required below or extra space inserted in text.
   \def\lyxNotebookPrintOn<<basic_cell_type>><<inset_specifier>>{%
      \ifthenelse{\equal{\lyxNotebookPrintingIsOff<<basic_cell_type>><<inset_specifier>>}{true}}{%
         \let\lyxNotebookCell<<basic_cell_type>><<inset_specifier>>=\oldLyxNotebookCell<<basic_cell_type>><<inset_specifier>>%
         \let\endlyxNotebookCell<<basic_cell_type>><<inset_specifier>>=\oldEndlyxNotebookCell<<basic_cell_type>><<inset_specifier>>%
         \def\lyxNotebookPrintingIsOff<<basic_cell_type>><<inset_specifier>>{false}%
      }%
      {}%
   }%

   % Build up the general printing off/on commands by adding commands for the
   % inset specifier <<inset_specifier>> and basic cell type <<basic_cell_type>>
   % (Note expandafter is used to avoid recursion problems; using e.g.
   % \let\oldegg\egg and then using oldegg on the r.h.s. should also work.)
   \ifthenelse{\isundefined{\lyxNotebookPrintOff}}{\def\lyxNotebookPrintOff{}}{}
   \expandafter\def\expandafter\lyxNotebookPrintOff\expandafter{\lyxNotebookPrintOff\lyxNotebookPrintOff<<basic_cell_type>><<inset_specifier>>}
   \ifthenelse{\isundefined{\lyxNotebookPrintOn}}{\def\lyxNotebookPrintOn{}}{}
   \expandafter\def\expandafter\lyxNotebookPrintOn\expandafter{\lyxNotebookPrintOn\lyxNotebookPrintOn<<basic_cell_type>><<inset_specifier>>}
"""

# This ends the preamble section of the module, and is appended to the above after
# the language-specific preamble from the language's spec file is appended.
module_header_template_end = \
    r"""

EndPreamble
"""

# ======================================================
# Define the basic template for Standard and Init cells.
# ======================================================

standard_template = \
    r"""

InsetLayout Flex:LyxNotebookCell:<<basic_cell_type>>:<<inset_specifier>>
        # Flex custom layouts work with flex-insert, but exact case matters, e.g.,
        #    flex-insert Flex:WrapListings
        # Also works with inset-forall:
        #    inset-forall Flex:WrapListings self-insert egg
        # but puts "egg" before the inset, not inside it.  The operations can also
        # be applied to any prefix, split at a colon, to apply to larger groups.
   LyXType              custom
   #
   # Spacing and newlines.
   #
   FreeSpacing          true
   PassThru             true # true for raw, false to do Latex processing on text
   SpellCheck           false
   # NewLine              false # whether newlines are translated into Latex \\
   ParbreakIsNewline    true
   KeepEmpty            true # keep empty lines
   ForceLTR             true # not sure why, but similar modules set it
   MultiPar             true
   ForcePlain           true # force Plain Layout, so user cannot change
   <<EditExternalTag>>
   # custompars false stops blue highlighting on update, inset-select-all still works
   # CustomPars           false # cannot use "paragraph settings" dialog inside inset
   #
   # Labels, fonts, and colors.
   #
   LabelString          "<<inset_specifier>> <<label_modifier>> Code"
   Decoration           classic
   BgColor              white
   Font # the font of the text in Lyx, not the Latex font
      Color               foreground
      Size                Small
      # Family              Roman
      Family              Typewriter
      Shape               Up
      Series              Medium
   EndFont
   LabelFont # the font of the inset label in LyX, must be after Font
      # Color          collapsable
      Color          green
      Size           Small
   EndFont
   #
   # Latex-related settings.
   #
   LatexName            lyxNotebookCell<<basic_cell_type>><<inset_specifier>>
   # LatexType            command
   LatexType            Environment
   # RequiredArgs         0    # not used
   # LatexParam         "[fragile,allowframebreaks]" # example, not real params
   Requires             "listings,verbatim,ifthen,color,marginnote,needspace,graphicx,setspace,textcomp"
   # NeedProtect        true
   RefPrefix            "lyxCell"
   Preamble
      %
      % The preamble inserted by <<inset_specifier>> <<basic_cell_type>> InsetLayout.
      %
      \lstnewenvironment{lyxNotebookCell<<basic_cell_type>><<inset_specifier>>}{%
         \mbox{}% try to keep all on one line so margin notes stay with listings
         % -----------------------------------------------------------------------
         % Do color-related lstsets, according to user choice of color or not.
         % -----------------------------------------------------------------------
         \ifthenelse{\equal{\lyxNotebookNoColor}{true}}{%
            % --------------------------------------------------------------------
            % Begin then section of ifthenelse, formatting without color.
            % --------------------------------------------------------------------
            \lstset{style=lyxNotebookNoColor<<basic_cell_type>><<inset_specifier>>}%
         } % end then section of ifthenelse
         {  % -----------------------------------------------------------------------
            % Begin else section of ifthenelse, color formatting.
            % -----------------------------------------------------------------------
            \lstset{style=lyxNotebookColor<<basic_cell_type>><<inset_specifier>>}%
         } % end else section of ifthenelse
         % -----------------------------------------------------------------------
         % Now execute the any relevant user-defined lstset commands.
         % -----------------------------------------------------------------------
         \ifthenelse{\isundefined{\lyxNotebookLstsetAllAll}}%
         {} % do nothing if command is undefined
         {  % otherwise, the user defined it so call it
            \lyxNotebookLstsetAllAll%
         } % end of else section of ifthenelse for whether user lstset is defined
         % -----------------------------------------------------------------------
         \ifthenelse{\isundefined{\lyxNotebookLstset<<basic_cell_type>>All}}
         {} % do nothing if command is undefined
         {  % otherwise, the user defined it so call it
            \lyxNotebookLstset<<basic_cell_type>>All%
         } % end of else section of ifthenelse for whether user lstset is defined
         % -----------------------------------------------------------------------
         \ifthenelse{\isundefined{\lyxNotebookLstsetAll<<inset_specifier>>}}
         {} % do nothing if command is undefined
         {  % otherwise, the user defined it so call it
            \lyxNotebookLstsetAll<<inset_specifier>>%
         } % end of else section of ifthenelse for whether user lstset is defined
         % -----------------------------------------------------------------------
         \ifthenelse{\isundefined{\lyxNotebookLstset<<basic_cell_type>><<inset_specifier>>}}
         {} % do nothing if command is undefined
         {  % otherwise, the user defined it so call it
            \lyxNotebookLstset<<basic_cell_type>><<inset_specifier>>%
         } % end of else section of ifthenelse for whether user lstset is defined
         % -----------------------------------------------------------------------
         % Put a rotated, bold, ttfamily "<<prog_name>>"
         % always in the right margin.
         % -----------------------------------------------------------------------
         \ifthenelse{\equal{\lyxNotebookNoCellLabels}{false}}{%
            %
            % The \needspace command keeps the marginnote together with the listing
            % even on pagebreaks.
            %
            % The \leavevmode (or an empty \mbox{}) keeps the marginnote aligned
            % with the top of the listing even when \flushbottom adds vertical
            % space.  It does so by keeping everything on same line.  Not all are
            % probably needed, but it seems to work somewhat.  As a last
            % resort one could temporarily set \raggedbottom.
            %
            % The use of two \marginnote commands (each with an empty slot) is to
            % keep the margin note to the right, even when twosided styles are used.
            %
            \mbox{}%
            %\Needspace*{\lyxNotebookNeedspaceLabelValue}% exact, flushbottom
            %\Needspace{\lyxNotebookNeedspaceLabelValue}% exact but not flushbottom
            \needspace{\lyxNotebookNeedspaceLabelValue}% not flushbottom, approx
            {\reversemarginpar\marginnote[]{\rotatebox{-90}{\lyxNotebookLabelFormat <<prog_name>>}}[0.8em]}\marginnote[]{\rotatebox{-90}{\lyxNotebookLabelFormat <<prog_name>>}}[0.8em]%
            %{\reversemarginpar % this gets the "always to right" for even & odd pages
            %\marginpar[\rotatebox{-90}{\bfseries\ttfamily\tiny <<prog_name>>}]{rrev}}
            %\marginpar[lplain]{\rotatebox{-90}{\bfseries\ttfamily\tiny <<prog_name>>}}
            \nopagebreak%
         } % end of do label-printing
         {} % do nothing when lyxNotebookNoCellLabels is true
         % -----------------------------------------------------------------------
      }% end of lstnewenvironment starting code block
      { % begin of lstnewenvironment ending code block
         % try to avoid breaks between code cells and output cells (if output printed)
         \ifthenelse{\equal{\lyxNotebookPrintingIsOffOutput<<inset_specifier>>}{false}}{%
         \nopagebreak
         }{}%
      }% end of lstnewenvironment ending code block
   EndPreamble
End
"""


# ===========================================
# Define the basic template for Output cells.
# ===========================================

output_template = \
    r"""

InsetLayout Flex:LyxNotebookCell:Output:<<inset_specifier>>
        # Flex custom layouts work with flex-insert, but exact case matters, e.g.,
        #    flex-insert Flex:WrapListings
        # Also works with inset-forall:
        #    inset-forall Flex:WrapListings self-insert egg
        # but puts "egg" before the inset, not inside it.  The operations can also
        # be applied to any prefix, split at a colon, to apply to larger groups.
   LyXType              custom
   #
   # Spacing and newlines.
   #
   FreeSpacing          true
   PassThru             true # true for raw, false to do Latex processing on text
   SpellCheck           false
   # NewLine              false # whether newlines are translated into Latex \\
   ParbreakIsNewline    true
   KeepEmpty            true # keep empty lines
   ForceLTR             true # not sure why, but similar modules set it
   MultiPar             true
   ForcePlain           true # force Plain Layout, so user cannot change
   <<EditExternalTag>>
   # custompars false stops blue highlighting on update, inset-select-all still works
   # CustomPars           false # cannot use "paragraph settings" dialog inside inset
   #
   # Labels, fonts, and colors.
   #
   LabelString          "<<inset_specifier>> Output"
   # Decoration           minimalistic
   Decoration           classic
   BgColor              white
   Font # the font of the text in Lyx, not the Latex font
      Color               foreground
      Size                Small
      # Family              Roman
      Family              Typewriter
      Shape               Up
      Series              Medium
   EndFont
   LabelFont # the font of the inset label in LyX, must be after Font
      # Color          collapsable
      Color          green
      Size           Small
   EndFont
   #
   # Latex-related settings.
   #
   LatexName            lyxNotebookCellOutput<<inset_specifier>>
   # LatexType            command
   LatexType            Environment
   # RequiredArgs         0    # not used
   # LatexParam         "[fragile,allowframebreaks]" # example, not real params
   Requires             "listings,verbatim,ifthen,textcomp"
   # NeedProtect        true
   RefPrefix            "lyxCell"
   Preamble
      %
      % The preamble inserted by <<inset_specifier>> Output InsetLayout.
      %

      % calculate the length of spacing between two listings, to remove it
      \ifthenelse{\isundefined{\doubleskipamount}}{\newlength{\doubleskipamount}}{}
      \setlength{\doubleskipamount}{-\medskipamount}
      \addtolength{\doubleskipamount}{2pt}

      \lstnewenvironment{lyxNotebookCellOutput<<inset_specifier>>}{
         \nopagebreak % try to keep on the same page as standard cell above it
         % -----------------------------------------------------------------------
         % Do color-related lstsets, according to user choice of color or not.
         % -----------------------------------------------------------------------
         \ifthenelse{\equal{\lyxNotebookNoColor}{true}}{
            % --------------------------------------------------------------------
            % Begin then section of ifthenelse, formatting without color.
            % --------------------------------------------------------------------
            \lstset{style=lyxNotebookNoColorOutput<<inset_specifier>>}
         } % end then section of ifthenelse
         {
            % -----------------------------------------------------------------------
            % Begin else section of ifthenelse, color formatting.
            % -----------------------------------------------------------------------
            \lstset{style=lyxNotebookColorOutput<<inset_specifier>>}
         } % end else section of ifthenelse
         % -----------------------------------------------------------------------
         % Now execute the any relevant user-defined lstset commands.
         % -----------------------------------------------------------------------
         \ifthenelse{\isundefined{\lyxNotebookLstsetAllAll}}
         {} % do nothing if command is undefined
         {  % otherwise, the user defined it so call it
            \lyxNotebookLstsetAllAll
         } % end of else section of ifthenelse for whether user lstset is defined
         % -----------------------------------------------------------------------
         \ifthenelse{\isundefined{\lyxNotebookLstset<<basic_cell_type>>All}}
         {} % do nothing if command is undefined
         {  % otherwise, the user defined it so call it
            \lyxNotebookLstset<<basic_cell_type>>All
         } % end of else section of ifthenelse for whether user lstset is defined
         % -----------------------------------------------------------------------
         \ifthenelse{\isundefined{\lyxNotebookLstsetAll<<inset_specifier>>}}
         {} % do nothing if command is undefined
         {  % otherwise, the user defined it so call it
            \lyxNotebookLstsetAll<<inset_specifier>>
         } % end of else section of ifthenelse for whether user lstset is defined
         % -----------------------------------------------------------------------
         \ifthenelse{\isundefined{\lyxNotebookLstset<<basic_cell_type>><<inset_specifier>>}}
         {} % do nothing if command is undefined
         {  % otherwise, the user defined it so call it
            \lyxNotebookLstset<<basic_cell_type>><<inset_specifier>>
         } % end of else section of ifthenelse for whether user lstset is defined
      }% end of lstnewenvironment starting code block
      {}% all of lstnewenvironment ending code (empty)
   EndPreamble
End
"""

# ==================================================================================
# Define the basic template for the module to redefine Listings to use a small font.
# This module makes Listings display with the same size font as the Lyx Notebook insets.
# ==================================================================================

listings_with_small_font = \
    r"""#\DeclareLyXModule{Listings with Small Font}
#DescriptionBegin
#Changes the built-in LyX listings insets to use a small font in the LyX display.
#Nothing about how the code is formatted for printing is changed.  Distributed
#with the LyX Notebook program for consistency in the appearance of code in
#insets.
#DescriptionEnd

# Author : alb
#
# THIS FILE IS AUTOMATICALLY GENERATED BY generateModuleFilesFromTemplate.py
# Modifications can be made, but they will be overwritten if it is run again.

#Format 21
Format 66
#Format 80

Requires "listings"

InsetLayout Listings
   CopyStyle           Listings
   BgColor             white
   Font # the font of the text in Lyx, not the Latex font
      Color               foreground
      Size                Small
      Family              Typewriter
      Shape               Up
      Series              Medium
   EndFont
End
"""


#
# ==========================================================================
# Generate the files from the templates
# ==========================================================================
#

def do_replacements(string, replacement_dict):
    """Return the string `string` with all the keys/meta-vars in `replacement_dict`
    replaced by their values."""
    for key in replacement_dict:
        string = string.replace(key, replacement_dict[key])
    return string


def generate_module_files_from_templates(dirname, has_editable_insets):
    """Generate files, in the directory `dirname`."""
    # This tag is new in 4.0.  Left out unless has_editable_insets is true.
    edit_external_tag = "EditExternal         true # enable inset-edit to work"
    edit_external_tag = edit_external_tag if has_editable_insets else ""

    prev_dir = os.curdir
    os.chdir(dirname)

    # First do the Listings redefinition, since it just needs to be written out.
    with open("lyxNotebookListingsWithSmallFont.module", "w") as f:
        f.write(listings_with_small_font)

    # Now do all the other modules, one for each interpreter specification.
    for spec in all_specs:
        # Get some language-specific variable settings from the spec.
        preamble_latex_code = spec.preamble_latex_code
        inset_specifier = spec.params["inset_specifier"] # E.g., Python or Bash in LyX code.
        prog_name = spec.params["prog_name"] # Like inset_specifier, but the displayed name.
        lst_language = spec.params["listings_language"] # For listings style, e.g., python.

        print("running for inset_specifier=" + inset_specifier
              + ",  prog_name=" + prog_name + ",  listings_language=" + lst_language)

        replacement_dict = {
            "<<EditExternalTag>>": edit_external_tag,
            "<<triple_quote>>": "\"\"\"",
            "<<triple_quote>>": "\"\"\"",
            "<<inset_specifier>>": inset_specifier,
            "<<prog_name>>": prog_name,
            "<<label_modifier>>": "", # This adds a modifier to the Lyx cell label.
            "<<lst_language>>": lst_language,
            }

        # Replace meta-vars in the common header section.
        header_common = do_replacements(module_header_template_common, replacement_dict)

        # Replace meta-vars in dependent header, one copy for each basic_cell_type.
        header_dependent_concat = ""
        for basic_cell_type in ["Init", "Standard", "Output",]: # "Noprint"]:
            replacement_dict["<<basic_cell_type>>"] = basic_cell_type
            header_dependent_concat += do_replacements(
                    module_header_template_basic_cell_type_dependent, replacement_dict)

        # Replace certain meta-vars in preamble_latex_code.
        preamble_latex_code = do_replacements(preamble_latex_code, replacement_dict)

        # Replace meta-vars in init template.
        # Init cells are currently identical to standard cells except for the frame spec
        replacement_dict["<<basic_cell_type>>"] = "Init"
        replacement_dict["<<label_modifier>>"] = "Init"
        init = do_replacements(standard_template, replacement_dict)

        # Replace meta-vars in standard template.
        replacement_dict["<<basic_cell_type>>"] = "Standard"
        replacement_dict["<<label_modifier>>"] = "" # Standard is default.
        standard = do_replacements(standard_template, replacement_dict)

        # Replace meta-vars in output template.
        replacement_dict["<<basic_cell_type>>"] = "Output"
        output = do_replacements(output_template, replacement_dict)

        # Replace meta-vars in noprint template.
        # TODO: Adding noprint messes up the Latex PDF generation...
        #replacement_dict["<<basic_cell_type>>"] = "Noprint"
        replacement_dict["<<label_modifier>>"] = "NP" #
        #noprint = do_replacements(standard_template, replacement_dict)


        # Write concat of all templates to correct output file.
        combined_string = (header_common
                         + header_dependent_concat
                         + preamble_latex_code
                         + module_header_template_end
                         + init
                         + standard
                         + output
                         #+ noprint
                         )
        with open("lyxNotebookCell"+inset_specifier+".module", "w") as f:
            f.write(combined_string)

    os.chdir(prev_dir)

