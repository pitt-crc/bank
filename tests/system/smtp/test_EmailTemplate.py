"""Tests for the ``EmailTemplate`` class."""

from unittest import TestCase
from unittest.mock import call, patch

from bank.exceptions import FormattingError
from bank.system.smtp import EmailTemplate


class FieldIdentification(TestCase):
    """Test the identification of formattable fields"""

    def test_all_fields_found(self) -> None:
        """Test the template instance is aware of all fields"""

        self.assertCountEqual(('x', 'y'), EmailTemplate('{x} {y}').fields)

    def test_duplicate_fields(self) -> None:
        """Test fields with duplicate keys are returned as a single value"""

        self.assertEqual(('x',), EmailTemplate('{x} {x}').fields)

    def test_empty_return_for_no_fields(self) -> None:
        """Test the return is empty when there are no fields"""

        fields = EmailTemplate('there are no fields here').fields
        self.assertEqual(0, len(fields), f'Found fields: {fields}')


class Formatting(TestCase):
    """Test the formatting of the email template"""

    def test_message_is_formatted(self) -> None:
        """Test the returned instance has a formatted message"""

        formatted_template = EmailTemplate('Value: {x}').format(x=0)
        self.assertEqual('Value: 0', formatted_template.msg)

    def test_returns_copy(self) -> None:
        """Test formatting a message returns a copy"""

        original = EmailTemplate('Value: {x}')
        new = original.format(x=0)
        self.assertNotEqual(id(original), id(new))

    def test_partial_format_error(self) -> None:
        """Test for a ``ValueError`` when partially formatting a message"""

        with self.assertRaisesRegex(FormattingError, "Missing field names: {'y'}"):
            EmailTemplate('First Value: {x}, Second Value: {y}').format(x=0)

    def test_error_on_invalid_keys(self) -> None:
        """Test for a value error when given invalid field names"""

        with self.assertRaisesRegex(FormattingError, "Invalid field names: {'y'}"):
            EmailTemplate('Value: {x}').format(x=0, y=1)


class MessageSending(TestCase):
    """Tests for sending emails via an SMTP server"""

    @patch('smtplib.SMTP')
    def setUp(self, mock_smtp) -> None:
        """Set up and send a mock ``EmailTemplate``  instance"""

        self.template = EmailTemplate('This is a test')
        self.from_address = 'fake_sender@fake_domain.com'
        self.to_address = 'fake_recipient@fake_domain.com'
        self.subject = 'Subject line'
        self.mock_smtp = mock_smtp
        self.sent = self.template.send_to(
            self.to_address, self.subject, self.from_address, smtp=mock_smtp)

    def test_message_matches_template(self) -> None:
        """Test the email message matches the template"""

        # The rstrip removes a newline character that is added automatically in the delivered message
        sent_message = self.sent.get_body().get_content().rstrip()
        self.assertEqual(self.template.msg, sent_message)

    def test_address_fields_are_set(self) -> None:
        """Test the address/subject fields have been set in the delivered email"""

        self.assertEqual(self.to_address, self.sent['To'])
        self.assertEqual(self.from_address, self.sent['From'])
        self.assertEqual(self.subject, self.sent['Subject'])

    def test_message_is_sent(self) -> None:
        """Test the smtp server is given the email message to send"""

        self.assertIn(call().send_message(self.sent), self.mock_smtp.__enter__.mock_calls)

    @patch('smtplib.SMTP')
    def test_error_on_incomplete_message(self, mock_smtp) -> None:
        """Test a ``RuntimeError`` is raised when sending an incomplete email message"""

        with self.assertRaises(FormattingError):
            EmailTemplate('{x}').send_to(self.to_address, self.subject, self.from_address, smtp=mock_smtp)
