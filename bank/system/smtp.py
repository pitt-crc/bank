"""Custom logic for the creation, formatting, and sending of email templates.

API Reference
-------------
"""

from __future__ import annotations

from email.message import EmailMessage
from logging import getLogger
from smtplib import SMTP
from string import Formatter
from typing import Any, Optional, Tuple, cast

from bs4 import BeautifulSoup

from bank.exceptions import FormattingError

LOG = getLogger('bank.system.smtp')


class EmailTemplate:
    """A formattable email template"""

    def __init__(self, template: str) -> None:
        """A formattable email template

        Email messages passed at init should follow the standard python
        formatting syntax. The message can be in plain text or in HTML format.

        Args:
            template: A partially unformatted email template
        """

        self._msg = template
        self._formatter = Formatter()

    @property
    def msg(self) -> str:
        """"Return the text content of the email template"""

        return self._msg

    @property
    def fields(self) -> Tuple[str]:
        """Return any unformatted fields in the email template

        Returns:
            A tuple of unique field names
        """

        # Create an iterator over all fields
        all_fields = (cast(str, field_name) for _, field_name, *_ in self._formatter.parse(self.msg))

        # Keep only unique fields that are not None
        unique_fields = set(field for field in all_fields if field is not None)
        return tuple(unique_fields)

    def format(self, **kwargs: Any) -> EmailTemplate:
        """Format the email template

        See the ``fields`` attribute for valid keyword argument names.

        Args:
            kwargs: Values used to format each field in the template

        Returns:
            A copy of the parent instance with a formatted message

        Raises:
            FormattingError: One missing or extra fields
        """

        passed_fields = set(kwargs)
        extra_fields = passed_fields - set(self.fields)
        if extra_fields:
            raise FormattingError(f'Invalid field names: {extra_fields}')

        missing_fields = set(self.fields) - passed_fields
        if missing_fields:
            raise FormattingError(f'Missing field names: {missing_fields}')

        return EmailTemplate(self._msg.format(**kwargs))

    def _raise_missing_fields(self) -> None:
        """Raise an error if the template message has any unformatted fields

        Raises:
            FormattingError: If the email template has unformatted fields
        """

        if any(self.fields):
            LOG.error('Could not send email. Missing fields found')
            raise FormattingError(f'Message has unformatted fields: {self.fields}')

    def send_to(self, to: str, subject: str, ffrom: str, smtp: Optional[SMTP] = None) -> EmailMessage:
        """Send the email template to the given address

        Args:
            to: The email address to send the message to
            subject: The subject line of the email
            ffrom: The address of the message sender
            smtp: optionally use an existing SMTP server instance

        Returns:
            A copy of the email message

        Raises:
            FormattingError: If the email template has unformatted fields
        """

        LOG.debug(f'Sending email to {to}')
        self._raise_missing_fields()

        # Extract the text from the email
        soup = BeautifulSoup(self._msg, "html.parser")
        email_text = soup.get_text()

        msg = EmailMessage()
        msg.set_content(email_text)
        msg.add_alternative(self._msg, subtype="html")
        msg["Subject"] = subject
        msg["From"] = ffrom
        msg["To"] = to

        with smtp or SMTP("localhost") as smtp_server:
            smtp_server.send_message(msg)

        return msg
