Command Line Interface
======================

Command line functions are grouped together by the service being administered:

.. code-block:: bash

   crc_bank.py <service> <action> --arguments

General Account Management
--------------------------

.. argparse::
   :module: bank.cli
   :func: AccountParser
   :path: account
   :prog: crc_bank.py

User Proposals
--------------

.. argparse::
   :module: bank.cli
   :func: ProposalParser
   :path: proposal
   :prog: crc_bank.py

User Investments
----------------

.. argparse::
   :module: bank.cli
   :func: InvestmentParser
   :path: investment
   :prog: crc_bank.py


Banking Administrative Tasks
----------------------------

.. argparse::
   :module: bank.cli
   :func: AdminParser
   :path: admin
   :prog: crc_bank.py
