"""The ``system`` module acts as an interface provides an object-oriented
interface for various command line utilities (e.g., ``sacctmgr``)
and system services (e.g., ``smtp``) installed on the parent system.

SubModules
----------

.. autosummary::
   :nosignatures:

   bank.system.ldap
   bank.system.shell
   bank.system.slurm
   bank.system.smtp
"""

from .shell import *
from .slurm import *
from .smtp import *
