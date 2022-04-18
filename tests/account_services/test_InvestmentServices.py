from unittest import TestCase

from tests._utils import InvestmentSetup


class InitExceptions(InvestmentSetup, TestCase):

    def test_error_on_missing_proposal(self) -> None:
        """Test a ``MissingProposalError`` exception is raised if the account has no proposal"""

        with self.assertRaises(MissingProposalError):
            InvestmentData(account_name=settings.test_account)

    def test_error_proposal_is_class(self) -> None:
        """Test a ``ValueError`` is raised when managing investments for accounts with Class proposals"""

        account = ProposalData(settings.test_account)
        account.create_proposal(type=ProposalEnum.Class)
        with self.assertRaisesRegex(MissingProposalError, 'Investments cannot be added/managed for class accounts'):
            InvestmentData(account_name=settings.test_account)


class AdvanceInvestmentSus(InvestmentSetup, TestCase):
    """Tests for the withdrawal of service units from a single investment"""

    def test_investment_is_advanced(self) -> None:
        """Test the specified number of service units are advanced from the investment"""

        # Advance half the available service units
        self.account.advance(1_500)

        with Session() as session:
            investments = session.query(Investment) \
                .filter(Investment.account_name == settings.test_account) \
                .order_by(Investment.start_date) \
                .all()

        # Oldest investment should be untouched
        self.assertEqual(self.num_inv_sus, investments[0].service_units)
        self.assertEqual(2500, investments[0].current_sus)
        self.assertEqual(0, investments[0].withdrawn_sus)

        # Middle investment should be partially withdrawn
        self.assertEqual(self.num_inv_sus, investments[1].service_units)
        self.assertEqual(500, investments[1].current_sus)
        self.assertEqual(500, investments[1].withdrawn_sus)

        # Youngest (i.e., latest starting time) investment should be fully withdrawn
        self.assertEqual(self.num_inv_sus, investments[2].service_units)
        self.assertEqual(0, investments[2].current_sus)
        self.assertEqual(1_000, investments[2].withdrawn_sus)

    def test_error_if_overdrawn(self) -> None:
        """Test an ``ValueError`` is raised if the account does not have enough SUs to cover the advance"""

        with Session() as session:
            investments = self.account._get_investment(session)
            available_sus = sum(inv.service_units for inv in investments)

        with self.assertRaises(ValueError):
            InvestmentData(settings.test_account).advance(available_sus + 1)

    def test_error_on_nonpositive_argument(self) -> None:
        """Test an ``ValueError`` is raised for non-positive arguments"""

        for sus in (0, -1):
            with self.assertRaises(ValueError):
                InvestmentData(settings.test_account).advance(sus)

    def test_error_for_missing_investments(self) -> None:
        """Test a ``MissingInvestmentError`` is raised if there are no investments"""

        with Session() as session:
            session.query(Investment).filter(Investment.account_name == settings.test_account).delete()
            session.commit()

        with self.assertRaises(MissingInvestmentError):
            self.account.advance(10)
