from unittest import TestCase
from unittest.mock import patch

from bank.dao import ProposalData
from bank.exceptions import MissingProposalError, ProposalExistsError
from bank.orm import Session, Proposal
from bank.settings import app_settings



class PrintUsageInfo(GenericSetup, TestCase):

    @patch('builtins.print')
    def test_printed_text_is_not_empty(self, mocked_print) -> None:
        ProposalData(app_settings.test_account).print_usage_info()
        printed_text = '\n'.join(c.args[0] for c in mocked_print.mock_calls)
        self.assertTrue(printed_text)
