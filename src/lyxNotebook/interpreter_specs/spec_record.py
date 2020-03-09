"""

This is a simple data record that is used to store the interpreter parameters.

"""

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

