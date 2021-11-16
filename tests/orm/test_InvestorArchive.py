"""Tests for the ``Investor`` class"""

from unittest import TestCase

from bank.orm import InvestorArchive
from tests.orm import base_tests


class ServiceUnitsValidation(TestCase, base_tests.ServiceUnitsValidation):
    """Tests for the validation of the service units"""

    db_table_class = InvestorArchive
    columns_to_test = ('service_units',)
