Command Line Interface
======================

A command line interface is provided is provided with the source code
for running the analysis pipeline. Command line functions are grouped
together by the service being administered:

.. code-block:: bash

   crc_bank.py <service> <action> --arguments

General Account Management
--------------------------

.. argparse::
   :module: bank.cli
   :func: CLIParser
   :path: admin
   :prog: crc_bank.py

User Proposals
--------------

.. argparse::
   :module: bank.cli
   :func: CLIParser
   :path: proposal
   :prog: crc_bank.py

User Investments
----------------

.. argparse::
   :module: bank.cli
   :func: CLIParser
   :path: investment
   :prog: crc_bank.py
