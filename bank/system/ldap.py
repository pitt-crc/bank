from ldap3 import Server, Connection

from bank.exceptions import LdapUserNotFound


def check_ldap_user(username):
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
    if len(pitt_ad_connection.entries) == 0:
        raise LdapUserNotFound(
            "Error: user {0} doesn't exist in Pitt AD".format(username)
        )
    else:
        return True
