Command Line Interface
======================

Command line functions are grouped together by the service being administered:

.. code-block:: bash

   crc_bank.py <service> <action> --arguments

General Account Management
--------------------------

.. argparse::
   :module: bank.cli.parsers
   :func: AccountParser
   :prog: crc_bank.py

User Proposals
--------------

.. argparse::
   :module: bank.cli.parsers
   :func: ProposalParser
   :prog: crc_bank.py

User Investments
----------------

.. argparse::
   :module: bank.cli.parsers
   :func: InvestmentParser
   :prog: crc_bank.py


Banking Administrative Tasks
----------------------------

.. argparse::
   :module: bank.cli.parsers
   :func: AdminParser
   :prog: crc_bank.py
