# Configuration file for the Sphinx documentation builder.
# See the documentation: https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

import sys
from pathlib import Path

package_source_path = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(package_source_path))

# -- Project information -----------------------------------------------------

project = 'CRC Bank'
copyright = '2021, Pitt CRC'
author = 'Pitt CRC, Barry Moore II'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings.
# Note: ``sphinx.ext.napoleon`` need to be loaded BEFORE ``sphinx_autodoc_typehints``
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.autosummary',
    'sphinx.ext.doctest',
    'sphinx.ext.napoleon',
    'sphinx_copybutton',
    'sphinx_rtd_theme',
    'sphinxarg.ext',
    'sphinx.ext.githubpages'
]

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_css_files = ['css/custom.css']
