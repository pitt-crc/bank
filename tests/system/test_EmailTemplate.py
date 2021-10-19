from unittest import TestCase
from unittest.mock import patch, call

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


class FieldIdentification(TestCase):
    """Tests for the identification of fields"""

    def test_all_fields_found(self) -> None:
        """Test the template instance is aware of all fields"""

        self.assertEqual(('x', 'y'), EmailTemplate('{x} {y}').fields)

    def test_empty_return_for_no_fields(self) -> None:
        """Test the return is empty when there are no fields"""

        fields = EmailTemplate('there are no fields here').fields
        self.assertEqual(0, len(fields), f'Found fields: {fields}')


class MessageSending(TestCase):
    """Tests for sending emails via an SMTP server"""

    @patch('smtplib.SMTP')
    def setUp(self, mock_smtp) -> None:
        self.template = EmailTemplate('This_is_a_test')
        self.from_address = 'fake_sender@fake_domain.com'
        self.to_address = 'fake_recipient@fake_domain.com'
        self.subject = 'Subject line'
        self.mock_smtp = mock_smtp
        self.sent = self.template.send_to(
            self.to_address, self.subject, self.from_address, smtp=mock_smtp)

    def test_message_matches_template(self) -> None:
        """Test the email message matches the template"""

        self.assertEqual(self.template.msg, self.sent.get_content())

    def test_email_fields_are_set(self) -> None:
        """Test the address/subject fields have been set in the sent email"""

        self.assertEqual(self.to_address, self.sent['To'])
        self.assertEqual(self.from_address, self.sent['From'])
        self.assertEqual(self.subject, self.sent['Subject'])

    def test_message_is_sent(self) -> None:
        """Test the smtp server is given the email message to send"""

        self.assertEqual(
            self.mock_smtp.return_value.sendmail.mock_calls,
            [call(self.template.msg)]
        )


class StringRepresentation(TestCase):
    """Tests for the casting of email templates into strings"""

    def runTest(self) -> None:
        template = EmailTemplate('This_is_a_test')
        self.assertEqual(template.msg, str(template))
