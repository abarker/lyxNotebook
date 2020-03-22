# -*- encoding: utf-8 -*-
"""

A setuptools-based setup module.
See: https://packaging.python.org/en/latest/distributing.html
Docs on the setup function kwargs:
   https://packaging.python.org/distributing/#setup-args

"""

from __future__ import absolute_import, print_function
import glob
import os.path
from setuptools import setup, find_packages
import codecs # Use a consistent encoding.
import shutil
import re

# Get the version data from the __init__.py file __version__ variable.
with open(os.path.join("src", "lyxnotebook", "__init__.py")) as f:
    __version__ = re.search(r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read()).group(1)

# To package external data, which includes an executable, the package_dir
# option tends to be better than the data_files option, which does not preserve
# the directory structure and puts the data in the wrong place for package data
# upon installation.  To use package_data all directory names must be valid
# package names, though, and you also need an __init__.py in each such
# directory and subdirectory.

# Paths to data files, relative to the main package directory.
lyxnotebook_bindings = os.path.join(
               "templates_for_bind_files", "lyxNotebookKeyBindings.template")
user_customizable_bindings = os.path.join(
               "templates_for_bind_files", "userCustomizableKeyBindings.template")
default_config_file = os.path.join(
               "default_config_file_and_data_files", "default_config_file.cfg")
bashrc_file = os.path.join(
               "default_config_file_and_data_files", "lyxNotebookBashrc.bash")

package_dir = {"": "src"} # Note src isn't used in later dotted package paths, set here!
packages = find_packages("src") # Finds submodules (otherwise need explicit listing).
py_modules = [os.path.splitext(
                 os.path.basename(path))[0]
                     for path in glob.glob("src/*.py")] # Only non-pkg modules.

# Get the long description from the README.rst file.
current_dir = os.path.abspath(os.path.dirname(__file__))
with codecs.open(os.path.join(current_dir, "README.rst"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="lyxnotebook",
    version=__version__, # <majorVersion>.<minorVersion>.<patch> format, (see PEP440)
    description="Use LyX like a code-executing notebook.",
    keywords=["LyX", "LaTeX", "TeX", "notebook"],
    install_requires=["wheel", "PySimpleGUI>=4.16.0"],
    url="https://github.com/abarker/lyxNotebook",
    entry_points = {
         "console_scripts": ["lyxnotebook = lyxnotebook.entry_points:run_lyxnotebook",
                             "lyxnotebook-from-lfun = lyxnotebook.entry_points:run_lyxnotebook_from_LFUN",]
        },
    #scripts=['bin/funniest-joke'],
    license="GPL",
    classifiers=[
        # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
        # Development Status: Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        #"Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        # uncomment if you test on these interpreters:
        # "Programming Language :: Python :: Implementation :: IronPython",
        # "Programming Language :: Python :: Implementation :: Jython",
        # "Programming Language :: Python :: Implementation :: Stackless",
        "Topic :: Utilities",
    ],

    # Settings usually the same.
    author="Allen Barker",
    author_email="Allen.L.Barker@gmail.com",

    #include_package_data=True, # Not set True when package_data is set.
    package_data={"lyxnotebook":[lyxnotebook_bindings, user_customizable_bindings,
                                 default_config_file, bashrc_file]},
    zip_safe=False,

    # Automated stuff below
    long_description=long_description,
    packages=packages,
    package_dir=package_dir,
    py_modules=py_modules,
)


