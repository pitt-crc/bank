from ldap3 import Server, Connection

from bank.exceptions import LdapUserNotFound, LDAPGroupNotFound
from bank.system import ShellCmd


def check_ldap_group(account: str, raise_if_false=False) -> bool:
    cmd = ShellCmd("getent group {0}".format(account))
    return_val = bool(cmd.out)

    if raise_if_false and not return_val:
        raise LDAPGroupNotFound(f"ERROR: The LDAP group {account} can't be found!")

    return return_val


def check_ldap_user(username: str, raise_if_false=False) -> bool:
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
