from logging import getLogger
from typing import List

from bank.exceptions import MissingProposalError
from bank.orm import Investor, Proposal, Session
from bank.settings import app_settings
from bank.utils import RequireRoot, ShellCmd

LOG = getLogger('bank.dao')


class Account:
    """Represents settings associated with individual user accounts"""

    def __init__(self, account_name: str) -> None:
        """Data access for user account information

        args:
            account_name: The name of the user account
        """

        self._account_name = account_name

    @property
    def email(self) -> str:
        """The email associated with the given user account"""

        cmd = ShellCmd(f'sacctmgr show account {self.account_name} -P format=description -n')
        return f'{cmd.out}{app_settings.email_suffix}'

    @property
    def account_name(self) -> str:
        """The name of the user account"""

        return self._account_name

    @property
    def proposal(self) -> Proposal:
        """The primary proposal assigned to the user account"""

        with Session() as session:
            proposal = session.query(Proposal).filter_by(account=self.account_name).first()

        if proposal is None:
            raise MissingProposalError(f'Proposal for account `{self.account_name}` does not exist.')

        return proposal

    @property
    def investments(self) -> List[Investor]:
        """List of investments assigned to the user account"""

        with Session() as session:
            return session.query(Investor).filter_by(account=self.account_name).all()

    @property
    def locked_state(self) -> bool:
        """Return whether the account is locked"""

        cmd = f'sacctmgr -n -P show assoc account={self.account_name} format=grptresrunmins'
        return 'cpu=0' in ShellCmd(cmd).out

    @RequireRoot
    def set_locked_state(self, locked: bool, notify: bool = False) -> None:
        """Lock or unlock the user account

        Args:
            locked: The new lock state to set
            notify: Send an email notifying the account holder of the new locked state
        """

        LOG.info(f'Setting lock state for account `{self.account_name}` to `{locked}`')

        # Construct a shell command using the ``sacctmgr`` command line tool
        lock_state_int = 0 if locked else -1
        clusters = ','.join(app_settings.clusters)
        cmd = f'sacctmgr -i modify account where account={self.account_name} cluster={clusters} set GrpTresRunMins=cpu={lock_state_int}'
        ShellCmd(cmd).raise_err()

        if notify:
            self.notify(app_settings.proposal_expires_notification)

    def notify(self, message_template):
        """Set an email notification to the user account

        Args:
            message_template: Template for the email message to send
        """

        LOG.debug(f'Sending email notification to account `{self.account_name}` ({self.email})')
        raise NotImplementedError()
