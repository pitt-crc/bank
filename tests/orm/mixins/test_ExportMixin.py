from unittest import TestCase

from bank.orm.mixins import ExportMixin
from .utils import create_table_with_mixin

DummyTable = create_table_with_mixin(ExportMixin)


class ExportingToJson(TestCase):
    ...
