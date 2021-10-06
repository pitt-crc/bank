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
    'sphinx_autodoc_typehints',
    'sphinx_rtd_theme',
    'sphinxarg.ext',
    'sphinxcontrib.sadisp',
    'sphinx.ext.githubpages'
]

# Configuration options for sphinxcontrib.sadisp
graphviz = 'dot -Tpng'.split()
sadisplay_default_render = 'graphviz'

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'


def skip(app, what, name, obj, skip, options):
    if name == "__init__":
        return False
    return skip


def setup(app):
    app.connect("autodoc-skip-member", skip)
