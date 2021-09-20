from unittest import TestCase


class SubparserNames(TestCase):
    """Test the names of various subparsers can be parsed"""

    test_names = [
        'insert', 'modify', 'add', 'change', 'renewal', 'date',
        'date_investment', 'investor', 'withdraw', 'info', 'usage',
        'check_sus_limit', 'check_proposal_end_date', 'check_proposal_violations',
        'get_sus', 'release_hold', 'reset_raw_usage', 'find_unlocked', 'lock_with_notification'
    ]
