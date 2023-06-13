"""The ``system`` module provides an object-oriented interface for various
command line utilities and system services.

SubModules
----------

.. autosummary::
   :nosignatures:

   bank.system.shell
   bank.system.slurm
   bank.system.smtp
"""

from .shell import *
from .slurm import *
from .smtp import *
