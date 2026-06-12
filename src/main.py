"""
main.py — Einstiegspunkt für email_archiver

Ablauf:
  1. Konfiguration aus config/config.ini einlesen
  2. Logging initialisieren (Datei + Konsole)
  3. IMAP-Verbindung zu Strato herstellen
  4. Alle E-Mails aus source_folder abrufen
  5. Jede E-Mail in PDF konvertieren und im output_folder speichern
  6. Erfolgreich verarbeitete E-Mails in processed_folder verschieben
  7. Fehlgeschlagene E-Mails im source_folder belassen, Fehler loggen
  8. Abschluss-Zusammenfassung ausgeben

Verwendung:
  python src/main.py
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# --- Arbeitsverzeichnis auf Projektwurzel setzen, src/ zu sys.path hinzufügen ---
# Damit config/, logs/ etc. relativ zur Projektwurzel gefunden werden
# und Imports aus src/ (utils, imap_client, converter) funktionieren.
_project_root = Path(__file__).parent.parent
os.chdir(_project_root)
sys.path.insert(0, str(Path(__file__).parent))

from ahlib import create_extended_logger, load_structured_config

import imap_client as imap
import converter
from utils import build_pdf_filename, decode_mime_header


def load_config(config_path: str, logger) -> object:
    """
    Liest die Konfigurationsdatei ein und gibt sie zurück.

    Args:
        config_path (str): Pfad zur INI-Datei, relativ zur Projektwurzel
        logger: ExtendedLogger-Instanz für Fehlermeldungen

    Returns:
        StructuredConfigParser: Geladene Konfiguration

    Raises:
        FileNotFoundError: Wenn config.ini nicht existiert
    """
    if not Path(config_path).exists():
        raise FileNotFoundError(
            f"Konfigurationsdatei nicht gefunden: {config_path}\n"
            f"Bitte config/config.ini.template nach config/config.ini kopieren und anpassen."
        )
    return load_structured_config(config_path, logger)


def ensure_output_folder(folder_path: str) -> Path:
    """
    Stellt sicher, dass der Ausgabeordner für PDFs existiert (legt ihn ggf. an).

    Args:
        folder_path (str): Pfad zum Ausgabeordner aus der Konfiguration

    Returns:
        Path: Path-Objekt des Ausgabeordners
    """
    output = Path(folder_path)
    output.mkdir(parents=True, exist_ok=True)
    return output


def process_emails(
    client,
    source_folder: str,
    processed_folder: str,
    output_folder: Path,
    logger,
) -> tuple[int, int]:
    """
    Verarbeitet alle E-Mails im Quellordner: konvertiert sie zu PDF und verschiebt sie.

    Fehler einzelner E-Mails werden geloggt. Die Verarbeitung läuft mit der
    nächsten E-Mail weiter (kein Abbruch bei Einzelfehler).

    Args:
        client: Angemeldeter imapclient.IMAPClient
        source_folder (str): IMAP-Quellordner
        processed_folder (str): IMAP-Zielordner nach Verarbeitung
        output_folder (Path): Lokales Verzeichnis für PDF-Ausgabe
        logger: ExtendedLogger-Instanz

    Returns:
        tuple[int, int]: (Anzahl Erfolge, Anzahl Fehler)
    """
    emails = imap.fetch_emails(client, source_folder)

    if not emails:
        logger.info("Keine E-Mails zur Verarbeitung gefunden.")
        return 0, 0

    success_count = 0
    error_count = 0

    for msg_id, msg in emails:
        subject = decode_mime_header(msg.get("Subject", "(kein Betreff)"))
        from_addr = msg.get("From", "")
        date_str = msg.get("Date", "")

        logger.info(f'Verarbeite: "{subject}" von {decode_mime_header(from_addr)}')

        try:
            # PDF-Dateipfad nach Namenskonvention bestimmen
            pdf_path = build_pdf_filename(date_str, from_addr, output_folder)

            # E-Mail → PDF konvertieren und speichern
            converter.convert_and_save(msg, pdf_path)
            logger.info(f"  -> PDF gespeichert: {pdf_path.name}")

            # E-Mail in Zielordner verschieben
            imap.move_email(client, msg_id, processed_folder)
            logger.info(f"  -> E-Mail verschoben nach '{processed_folder}'")

            success_count += 1

        except Exception as exc:
            error_count += 1
            logger.error(
                f"  FEHLER bei E-Mail (ID={msg_id}, Betreff={subject!r}): {exc}"
            )

    return success_count, error_count


def main() -> None:
    """
    Hauptfunktion: Konfiguration laden, IMAP verbinden, E-Mails verarbeiten, zusammenfassen.
    """
    # --- Logging initialisieren ---
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"email_archiver_{timestamp}.log"
    logger = create_extended_logger(str(log_file), screen_output=True, script_name="email_archiver")

    logger.info("=" * 60)
    logger.info("email_archiver gestartet")
    logger.info("=" * 60)

    # --- Konfiguration laden ---
    try:
        config = load_config("config/config.ini", logger)
    except FileNotFoundError as exc:
        logger.error(str(exc))
        sys.exit(1)

    server = config.get("imap", "server")
    port = config.getint("imap", "port")
    username = config.get("imap", "username")
    password = config.get("imap", "password")
    source_folder = config.get("imap", "source_folder")
    processed_folder = config.get("imap", "processed_folder")
    output_folder_str = config.get("output", "folder")

    # --- Ausgabeordner sicherstellen ---
    output_folder = ensure_output_folder(output_folder_str)
    logger.info(f"PDF-Ausgabeordner: {output_folder}")

    # --- IMAP-Verbindung herstellen ---
    client = None
    try:
        logger.info(f"Verbinde mit {server}:{port} als {username} ...")
        client = imap.connect(server, port, username, password)

        # --- E-Mails verarbeiten ---
        success_count, error_count = process_emails(
            client, source_folder, processed_folder, output_folder, logger
        )

    except Exception as exc:
        logger.error(f"Kritischer Fehler: {exc}")
        sys.exit(1)

    finally:
        if client is not None:
            imap.disconnect(client)

    # --- Abschluss-Zusammenfassung ---
    logger.info("=" * 60)
    logger.info(f"Fertig -- Erfolgreich: {success_count}, Fehler: {error_count}")
    logger.info("=" * 60)

    if error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
