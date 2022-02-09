from unittest import TestCase

from bank.orm import Validators


class TestValidation(TestCase):
    """Tests for methods used to validate column values"""

    def test_service_unit_validation(self) -> None:
        """Tests for the validation of service unit values"""

        validator = Validators()

        with self.assertRaises(ValueError):
            validator.validate_service_units('dummy_key', -1)

        validator.validate_service_units('dummy_key', 0)
        validator.validate_service_units('dummy_key', 10)

    def test_percent_notified_validation(self) -> None:
        """Tests for the validation of percent notified values"""

        validator = Validators()

        with self.assertRaises(ValueError):
            validator.validate_percent_notified('dummy_key', -1)

        with self.assertRaises(ValueError):
            validator.validate_percent_notified('dummy_key', 101)

        validator.validate_percent_notified('dummy_key', 0)
        validator.validate_percent_notified('dummy_key', 10)
        validator.validate_percent_notified('dummy_key', 100)
