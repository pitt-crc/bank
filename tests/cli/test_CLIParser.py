from unittest import TestCase

from bank.cli import CLIParser


class SubparserNames(TestCase):
    """Test the names of various subparsers can be parsed"""

    test_names = [
        'insert', 'modify', 'add', 'change', 'renewal', 'date',
        'date_investment', 'investor', 'withdraw', 'info', 'usage',
        'check_sus_limit', 'check_proposal_end_date', 'check_proposal_violations',
        'get_sus', 'release_hold', 'reset_raw_usage', 'find_unlocked', 'lock_with_notification'
    ]

    def runTest(self) -> None:
        """Check each subparser name parses without error"""

        for subparser_name in self.test_names:
            try:
                CLIParser().parse_args([subparser_name])

            except:
                self.fail(f'Could not parse name {subparser_name}')
