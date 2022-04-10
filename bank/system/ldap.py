import ldap
import ldap.sasl
from ldap3 import Server, Connection

from bank.exceptions import LdapUserNotFound, LDAPGroupNotFound, CRCUserNotFound
from bank.system import ShellCmd
from bank.settings import xxx

def check_ldap_group(account: str, raise_if_false=False) -> bool:
    """Return Whether the given ldap group exists

    Args:
        account: The name of the account to check for
        raise_if_false: Raise an error if the return value is false

    Raises:
        LDAPGroupNotFound: If ``raise_if_false`` is True and the account does not exist
    """

    cmd = ShellCmd("getent group {0}".format(account))
    return_val = bool(cmd.out)

    if raise_if_false and not return_val:
        raise LDAPGroupNotFound(f"ERROR: The LDAP group {account} can't be found!")

    return return_val


def check_ldap_user(username: str, raise_if_false=False) -> bool:
    """Return whether the given LDAP user exists

    Args:
        username: The username to check for
        raise_if_false: Raise an error if the return value is false

    Raises:
        LdapUserNotFound: If ``raise_if_false`` is True and the user is not found
    """

    ldap_username = "crcquery"
    with open("/ihome/crc/scripts/crcquery.txt", "r") as f:
        ldap_password = f.readline().strip()

    pitt_ad_server = Server("pittad.univ.pitt.edu", port=389)
    pitt_ad_connection = Connection(
        pitt_ad_server,
        user="cn={0},ou=Accounts,dc=univ,dc=pitt,dc=edu".format(ldap_username),
        password=ldap_password,
        auto_bind=True,
    )
    pitt_ad_connection.search(
        "dc=univ,dc=pitt,dc=edu", "(&(objectClass=user)(|(cn={0})))".format(username)
    )

    return_val = bool(pitt_ad_connection.entries)
    if raise_if_false and not return_val:
        raise LdapUserNotFound(
            "Error: user {0} doesn't exist in Pitt AD".format(username)
        )

    return return_val


def check_crc_user(username: str, raise_if_false=False) -> bool:
    """Return whether the given username is a CRC user account

    Args:
        username: The username to check for
        raise_if_false: Raise an error if the return value is false

    Raises:
        CRCUserNotFound: If ``raise_if_false`` is True and the user is not found
    """

    ldap_username = "crcquery"
    with open("/ihome/crc/scripts/crcquery.txt", "r") as f:
        ldap_password = f.readline().strip()

    crc_ldap_object = ldap.initialize("ldap://sam-ldap-prod-01.cssd.pitt.edu")
    crc_ldap_object.start_tls_s()

    auth = ldap.sasl.sasl(
        {ldap.sasl.CB_AUTHNAME: ldap_username, ldap.sasl.CB_PASS: ldap_password},
        "PLAIN",
    )

    # Bind and Search
    crc_ldap_object.sasl_interactive_bind_s("", auth)
    result = crc_ldap_object.search_s(
        "ou=people,dc=frank,dc=sam,dc=pitt,dc=edu",
        ldap.SCOPE_SUBTREE,
        "(cn={0})".format(username),
    )

    crc_ldap_object.unbind_s()

    return_val = len(result) > 0
    if raise_if_false and not return_val:
        raise CRCUserNotFound("CRC user {} not found!".format(username))

    return return_val
