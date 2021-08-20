#!/usr/bin/env /ihome/crc/install/python/miniconda3-3.7/bin/python

"""Command line interface for the ``bank`` package"""

from bank.cli import CLIParser

if __name__ == '__main__':
    parsed_args = vars(CLIParser().parse_args())
    parsed_args.pop('function')(parsed_args)
