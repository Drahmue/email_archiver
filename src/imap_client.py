"""
imap_client.py — IMAP-Verbindung und E-Mail-Operationen für email_archiver

Stellt bereit:
  - connect()       : IMAP-Verbindung zu Strato herstellen und anmelden
  - fetch_emails()  : Alle E-Mails aus dem Quellordner abrufen
  - move_email()    : E-Mail in den Zielordner verschieben (MOVE, Fallback: COPY+DELETE)
  - disconnect()    : Verbindung sauber trennen

Verwendet imapclient (statt imaplib direkt), da imapclient die modified-UTF-7-Kodierung
von Ordnernamen mit Umlauten (RFC 3501) automatisch behandelt.
"""

import email
import logging
from email.message import Message

from imapclient import IMAPClient
from imapclient.exceptions import IMAPClientError

logger = logging.getLogger(__name__)


def connect(server: str, port: int, username: str, password: str) -> IMAPClient:
    """
    Stellt eine SSL-Verbindung zum IMAP-Server her und meldet sich an.

    Args:
        server (str): Hostname des IMAP-Servers (z.B. 'imap.strato.de')
        port (int): IMAP-Port (993 für SSL)
        username (str): Benutzername / E-Mail-Adresse
        password (str): Passwort

    Returns:
        IMAPClient: Angemeldeter IMAP-Client

    Raises:
        IMAPClientError: Bei Verbindungs- oder Anmeldefehler
    """
    client = IMAPClient(server, port=port, ssl=True)
    client.login(username, password)
    logger.info(f"IMAP-Verbindung hergestellt: {username}@{server}:{port}")
    return client


def fetch_emails(client: IMAPClient, source_folder: str) -> list[tuple[int, Message]]:
    """
    Ruft alle E-Mails aus dem angegebenen IMAP-Ordner ab.

    Der Ordner wird im Lese-Schreib-Modus geöffnet (readonly=False), damit
    Flags gesetzt und E-Mails verschoben werden können.

    Args:
        client (IMAPClient): Angemeldeter IMAP-Client
        source_folder (str): Name des Quellordners (z.B. '01 für Ablage')

    Returns:
        list[tuple[int, Message]]: Liste von (IMAP-Nachrichten-ID, geparste E-Mail).
                                   Leere Liste wenn keine E-Mails vorhanden.

    Raises:
        IMAPClientError: Wenn der Ordner nicht geöffnet werden kann
    """
    client.select_folder(source_folder, readonly=False)
    msg_ids = client.search(["ALL"])

    if not msg_ids:
        logger.info(f"Keine E-Mails in '{source_folder}' gefunden.")
        return []

    logger.info(f"{len(msg_ids)} E-Mail(s) in '{source_folder}' gefunden.")

    response = client.fetch(msg_ids, ["RFC822"])
    result = []
    for msg_id, data in response.items():
        raw_bytes = data[b"RFC822"]
        msg = email.message_from_bytes(raw_bytes)
        result.append((msg_id, msg))

    return result


def move_email(client: IMAPClient, msg_id: int, processed_folder: str) -> None:
    """
    Verschiebt eine E-Mail in den Zielordner.

    Versucht zuerst den IMAP MOVE-Befehl (RFC 6851, von Strato unterstützt).
    Schlägt das fehl, wird auf COPY + STORE \\Deleted + EXPUNGE zurückgefallen.

    Args:
        client (IMAPClient): Angemeldeter IMAP-Client
        msg_id (int): IMAP-Nachrichten-ID der zu verschiebenden E-Mail
        processed_folder (str): Zielordner (z.B. '01 für Ablage erledigt')

    Raises:
        IMAPClientError: Wenn weder MOVE noch COPY+DELETE erfolgreich sind
    """
    try:
        client.move([msg_id], processed_folder)
        logger.debug(f"Nachricht {msg_id} per IMAP MOVE nach '{processed_folder}' verschoben.")
    except (IMAPClientError, Exception) as exc:
        logger.debug(f"IMAP MOVE fehlgeschlagen ({exc}), Fallback auf COPY+DELETE.")
        client.copy([msg_id], processed_folder)
        client.set_flags([msg_id], [b"\\Deleted"])
        client.expunge()
        logger.debug(f"Nachricht {msg_id} per COPY+DELETE nach '{processed_folder}' verschoben.")


def disconnect(client: IMAPClient) -> None:
    """
    Trennt die IMAP-Verbindung sauber (LOGOUT).

    Args:
        client (IMAPClient): Angemeldeter IMAP-Client
    """
    try:
        client.logout()
        logger.info("IMAP-Verbindung getrennt.")
    except Exception as exc:
        logger.warning(f"Fehler beim IMAP-Logout (wird ignoriert): {exc}")
