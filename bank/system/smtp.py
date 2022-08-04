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

from bank.exceptions import MissingEmailFieldsError

LOG = getLogger('bank.system.smtp')


class EmailTemplate(Formatter):
    """A formattable email template"""

    def __init__(self, msg: str) -> None:
        """A formattable email template

        Email messages passed at init should follow the standard python
        formatting syntax. The message can be in plain text or in HTML format.

        Args:
            msg: A partially unformatted email template
        """

        self._msg = msg

    @property
    def msg(self) -> str:
        """"The text content of the email template"""

        return self._msg

    @property
    def fields(self) -> Tuple[str]:
        """Return any unformatted fields in the email template

        Returns:
            A tuple of unique field names
        """

        return tuple(cast(str, field_name) for _, field_name, *_ in self.parse(self.msg) if field_name is not None)

    def format(self, **kwargs: Any) -> EmailTemplate:
        """Format the email template

        See the ``fields`` attribute for valid keyword argument names.

        Args:
            kwargs: Values used to format each field in the template
        """

        return EmailTemplate(self._msg.format(**kwargs))

    def _raise_missing_fields(self) -> None:
        """Raise an error if the template message has any unformatted fields

        Raises:
            MissingEmailFieldsError: If the email template has unformatted fields
        """

        if any(field_name for _, field_name, *_ in self.parse(self.msg) if field_name is not None):
            LOG.error('Could not send email. Missing fields found')
            raise MissingEmailFieldsError(f'Message has unformatted fields: {self.fields}')

    def send_to(self, to: str, subject: str, ffrom: str, smtp: Optional[SMTP] = None) -> EmailMessage:
        """Send the email template to the given address

        Args:
            to: The email address to send the message to
            subject: The subject line of the email
            ffrom: The address of the message sender
            smtp: optionally use an existing SMTP server instance

        Returns:
            A copy of the sent email

        Raises:
            MissingEmailFieldsError: If the email template has unformatted fields
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
