"""Tests for the ``Investor`` class"""

from unittest import TestCase

from bank.orm import InvestorArchive
from tests.orm import _utils


class ServiceUnitsValidation(TestCase, _utils.ServiceUnitsValidation):
    """Tests for the validation of the service units"""

    db_table_class = InvestorArchive
    columns_to_test = ('service_units',)
