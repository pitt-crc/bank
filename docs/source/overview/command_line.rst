Command Line Interface
======================

A command line interface is provided is provided with the source code
for running the analysis pipeline. An outline of the command line arguments
and their default values is provided below.

.. argparse::
   :module: bank.cli
   :func: CLIParser
   :path: admin

.. argparse::
   :module: bank.cli
   :func: CLIParser
   :path: slurm

.. argparse::
   :module: bank.cli
   :func: CLIParser
   :path: proposal

.. argparse::
   :module: bank.cli
   :func: CLIParser
   :path: investment