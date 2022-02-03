"""The ``system`` module acts as an interface for the underlying runtime
environment and provides an object-oriented interface for interacting with
the parent system. It includes wrappers around various command line utilities
(e.g., ``sacctmgr``) and system services (e.g., ``smtp``).

Usage Example
-------------

.. doctest:: python

   >>> from bank import system
   >>>
   >>> # Run a shell command
   >>> cmd = system.ShellCmd("echo 'Hello World'")
   >>> print(cmd.out)
   Hello World

   >>> # Require root permissions for a function
   >>> @system.RequireRoot
   ... def foo():
   ...     print('This function requires root access')

API Reference
-------------
"""

from .slurm import *
from .smtp import *
