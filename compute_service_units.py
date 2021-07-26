#!/usr/bin/env /ihome/crc/install/python/miniconda3-3.7/bin/python
""" compute_service_units.py -- Replace "CRC Accounts w/ SUs" spreadsheet
Usage:
    compute_service_units.py [-n <nodes>] [-u <units>] [-s <factor>] [-c <percent>]

Options:
    -h --help                       Print this screen and exit
    -v --version                    Print the version of compute_service_units.py
    -n --nodes <nodes>              Number of nodes contributed [default: 1]
    -u --units <units>              Compute units per node [default: 24]
    -s --scaling <factor>           Scaling factor for partition in Slurm [default: 1]
    -c --contribution <percent>     The percent contributed to general queue [default: 80]
"""

from functools import reduce

from docopt import docopt

from utils import Left, Right, unwrap_if_right
from utils import check_service_units_valid as check_natural_number


def check_positive_float(v):
    try:
        r = float(v)
    except ValueError:
        return Left(f"Given `{v}` which isn't a number")
    if r <= 0.0:
        return Left(f"Found `{r}` but it must be positive")
    return Right(r)


def check_positive_percentage(v):
    try:
        r = float(v)
    except ValueError:
        return Left(f"Given `{v}` which isn't a number")
    if not (0.0 <= r <= 100.0):
        return Left(f"Found `{r}` but it must be between 0 and 100")
    return Right(r)


# 85% of all hours for 5 years
total_hours_of_operation = 0.85 * 5 * 365 * 24

args = docopt(__doc__, version="compute_service_units.py version 0.0.1")
args["--contribution"] = unwrap_if_right(
    check_positive_percentage(args["--contribution"])
)
args["--nodes"] = unwrap_if_right(check_positive_float(args["--nodes"]))
args["--scaling"] = unwrap_if_right(check_positive_float(args["--scaling"]))
args["--units"] = unwrap_if_right(check_natural_number(args["--units"]))

total_service_units = reduce(
    lambda x, y: x * y,
    [
        total_hours_of_operation,
        args["--contribution"],
        args["--nodes"],
        (args["--scaling"] / 100.0),
        args["--units"],
    ],
)

print(round(total_service_units))
