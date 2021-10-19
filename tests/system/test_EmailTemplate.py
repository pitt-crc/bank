from unittest import TestCase
from bank.system import EmailTemplate


class Formatting(TestCase):
    """Tests for the formatting of the email template"""

    def test_returns_copy(self) -> None:
        """Test formatting a message returns a copy"""

        original = EmailTemplate('Value: {x}')
        new = original.format(x=1)
        self.assertNotEqual(id(original), id(new))

    def test_message_is_formatted(self) -> None:
        """Test the email message is formatted after the function call"""

        formatted_template = EmailTemplate('Value: {x}').format(x=1)
        self.assertEqual('Value: 1', formatted_template.msg)

    def test_error_for_incorrect_keys(self) -> None:
        """Test a ``ValueError`` is raised for kwarg names that don't match fields"""

        with self.assertRaises(ValueError):
            EmailTemplate('Value: {x}').format(y=1)

    def test_all_fields_found(self) -> None:
        """Test the template instance is aware of all fields"""

        self.assertEqual(('x', 'y'), EmailTemplate('{x} {y}').fields)


class MessageSending(TestCase):
    def test_alternative_test_available(self) -> None:
        pass

    def test_subject_is_set(self) -> None:
        pass

    def test_address_fields(self) -> None:
        pass
