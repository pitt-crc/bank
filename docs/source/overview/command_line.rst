Command Line Interface
======================

A command line interface is provided is provided with the source code
for running the analysis pipeline. Command line functions are grouped
together by the service being administered:

.. code-block:: bash

   crc_bank.py <service> <action> --arguments

General Administrative Tasks
----------------------------

.. argparse::
   :module: bank.cli
   :func: CLIParser
   :path: admin

Slrum Account Management
------------------------

.. argparse::
   :module: bank.cli
   :func: CLIParser
   :path: slurm


User Proposals
--------------

.. argparse::
   :module: bank.cli
   :func: CLIParser
   :path: proposal

User Investments
----------------

.. argparse::
   :module: bank.cli
   :func: CLIParser
   :path: investment
