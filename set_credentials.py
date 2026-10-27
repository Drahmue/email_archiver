"""
set_credentials.py — legt das IMAP-Passwort im Windows-Schlüsselbund ab (Credential Manager).

Das Passwort wird nur abgefragt, nie angezeigt. Der Eintrag gilt nur für das Windows-Konto,
unter dem das Skript läuft — also unter dem Konto ausführen, unter dem auch der Task läuft.

Verwendung:
  .venv\\Scripts\\python.exe set_credentials.py
"""

import configparser
import getpass
import sys
from pathlib import Path

import keyring

KEYRING_SERVICE = "email_archiver"
CONFIG_PATH = Path(__file__).parent / "config" / "config.ini"


def main() -> None:
    """Liest den IMAP-Benutzernamen aus config.ini und speichert das eingegebene Passwort."""
    config = configparser.ConfigParser()
    if not config.read(CONFIG_PATH, encoding="utf-8"):
        sys.exit(f"config.ini fehlt: {CONFIG_PATH}")
    username = config.get("imap", "username")
    password = getpass.getpass(f"IMAP-Passwort für {username} (Eingabe unsichtbar): ")
    if not password:
        sys.exit("Kein Passwort eingegeben, abgebrochen.")
    keyring.set_password(KEYRING_SERVICE, username, password)
    print(f"Passwort gespeichert (Schlüsselbund, Dienst '{KEYRING_SERVICE}', Benutzer {username}).")


if __name__ == "__main__":
    main()
