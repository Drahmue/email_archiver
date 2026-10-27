"""
main.py — Einstiegspunkt für email_archiver

Ablauf:
  1. Konfiguration aus config/config.ini einlesen
  2. Logging initialisieren (Datei + Konsole), Monatsdatei logs/email_archiver_yyyy-MM.log
  3. Optional gemeinsame Sperre belegen ([run] lock_file): Task auf dem HauServer und
     Handstart auf AHMain laufen nie gleichzeitig; belegt → warten, dann Lauf überspringen (Exit 0)
  3b. IMAP-Verbindung zu Strato herstellen (Passwort aus dem Windows-Schlüsselbund,
     Fallback: [imap] password in der INI)
  4. Je Auftrag (Ablage aus [imap]/[output], optional Belege aus [belege]):
     a. Alle E-Mails aus source_folder abrufen
     b. Jede E-Mail in PDF konvertieren und im Ausgabeordner speichern
        (erst als .tmp, dann umbenennen — Folgeprozesse sehen nur fertige PDFs)
     c. Erfolgreich verarbeitete E-Mails in processed_folder verschieben
     d. Fehlgeschlagene E-Mails im source_folder belassen, Fehler loggen
  5. Abschluss-Zusammenfassung ausgeben

Verwendung:
  python src/main.py              # Produktiv
  python src/main.py --dry-run    # nur auflisten: kein PDF, nichts verschieben

Exit-Code: 0 = OK, 1 = Fehler (Konfiguration, Verbindung oder mindestens eine E-Mail)
"""

import argparse
import os
import re
import socket
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from email.message import Message
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

KEYRING_SERVICE = "email_archiver"


@dataclass
class Job:
    """Ein Verarbeitungsauftrag: IMAP-Quellordner → PDFs im Ausgabeordner → IMAP-Zielordner."""

    name: str
    source_folder: str
    processed_folder: str
    output_folder: Path


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


def _extract_message_id(msg: Message) -> str | None:
    """Gibt die bereinigte Message-ID zurück (ohne spitze Klammern), oder None."""
    mid = msg.get("Message-ID", "").strip()
    return mid.strip("<>") if mid else None


def _extract_referenced_ids(msg: Message) -> set[str]:
    """Sammelt alle Message-IDs aus References- und In-Reply-To-Headern."""
    ids: set[str] = set()
    for header in ("References", "In-Reply-To"):
        for match in re.findall(r"<([^>]+)>", msg.get(header, "")):
            ids.add(match)
    return ids


def filter_thread_superseded(
    emails: list[tuple[int, Message]], logger
) -> tuple[list[tuple[int, Message]], list[tuple[int, Message]]]:
    """
    Trennt E-Mails im Batch in zu-verarbeitende und überholte auf.

    Outlook und Thunderbird zitieren bei jedem Reply die gesamte Vorgeschichte im
    Body. Dadurch enthält die jüngste E-Mail eines Threads alle älteren vollständig.
    Eine E-Mail gilt als überholt, wenn ihre Message-ID im References- oder
    In-Reply-To-Header einer anderen E-Mail im selben Batch auftaucht.

    Args:
        emails: Liste von (IMAP-ID, geparste E-Mail) aus fetch_emails()
        logger: Logger für Überspring-Meldungen

    Returns:
        Tupel (zu_verarbeiten, überholte):
          - zu_verarbeiten: Blätter des Thread-Baums → PDF erzeugen + verschieben
          - überholte: ältere Glieder der Kette → nur verschieben, kein PDF
    """
    referenced_ids: set[str] = set()
    for _, msg in emails:
        referenced_ids.update(_extract_referenced_ids(msg))

    to_process = []
    superseded = []
    for msg_id, msg in emails:
        own_id = _extract_message_id(msg)
        if own_id and own_id in referenced_ids:
            subject = decode_mime_header(msg.get("Subject", "(kein Betreff)"))
            logger.info(f'  Übersprungen (von neuerer Antwort im Batch überholt): "{subject}"')
            superseded.append((msg_id, msg))
        else:
            to_process.append((msg_id, msg))

    return to_process, superseded


def save_pdf_atomic(msg: Message, pdf_path: Path) -> None:
    """
    Erzeugt das PDF zuerst unter <name>.pdf.tmp und benennt es danach um.

    Folgeprozesse, die den Ausgabeordner überwachen (z. B. belege_sammler für
    belege\\eingang), sehen so nie eine halb geschriebene PDF-Datei.

    Args:
        msg (Message): Geparste E-Mail
        pdf_path (Path): Endgültiger Zielpfad der PDF-Datei

    Raises:
        Exception: Fehler aus converter.convert_and_save (die .tmp-Datei wird entfernt)
    """
    tmp_path = pdf_path.with_name(pdf_path.name + ".tmp")
    try:
        converter.convert_and_save(msg, tmp_path)
        os.replace(tmp_path, pdf_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def process_emails(client, job: Job, logger, dry_run: bool = False) -> tuple[int, int]:
    """
    Verarbeitet alle E-Mails im Quellordner eines Auftrags: konvertiert sie zu PDF und verschiebt sie.

    Fehler einzelner E-Mails werden geloggt. Die Verarbeitung läuft mit der
    nächsten E-Mail weiter (kein Abbruch bei Einzelfehler).

    Args:
        client: Angemeldeter imapclient.IMAPClient
        job (Job): Auftrag mit IMAP-Quell-/Zielordner und Ausgabeordner
        logger: ExtendedLogger-Instanz
        dry_run (bool): Nur auflisten, kein PDF erzeugen, nichts verschieben

    Returns:
        tuple[int, int]: (Anzahl Erfolge, Anzahl Fehler)
    """
    logger.info(f"Auftrag '{job.name}': '{job.source_folder}' -> {job.output_folder}, "
                f"danach nach '{job.processed_folder}'")
    emails = imap.fetch_emails(client, job.source_folder)

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
            pdf_path = build_pdf_filename(date_str, from_addr, job.output_folder)

            if dry_run:
                logger.info(f"  -> DryRun: würde {pdf_path.name} schreiben und nach "
                            f"'{job.processed_folder}' verschieben")
                success_count += 1
                continue

            # E-Mail → PDF konvertieren und speichern
            save_pdf_atomic(msg, pdf_path)
            logger.info(f"  -> PDF gespeichert: {pdf_path.name}")

            # E-Mail in Zielordner verschieben
            imap.move_email(client, msg_id, job.processed_folder)
            logger.info(f"  -> E-Mail verschoben nach '{job.processed_folder}'")

            success_count += 1

        except Exception as exc:
            error_count += 1
            logger.error(
                f"  FEHLER bei E-Mail (ID={msg_id}, Betreff={subject!r}): {exc}"
            )

    return success_count, error_count


def read_jobs(config) -> list[Job]:
    """
    Liest die Verarbeitungsaufträge aus der Konfiguration.

    Auftrag 'ablage' (immer): [imap] source_folder/processed_folder, [output] folder.
    Auftrag 'belege' (optional, nur wenn Abschnitt [belege] vorhanden):
    [belege] source_folder/processed_folder/output_folder.

    Args:
        config: Geladene Konfiguration (StructuredConfigParser)

    Returns:
        list[Job]: Aufträge in Verarbeitungsreihenfolge
    """
    jobs = [Job("ablage",
                config.get("imap", "source_folder"),
                config.get("imap", "processed_folder"),
                Path(config.get("output", "folder")))]
    if config.has_section("belege"):
        jobs.append(Job("belege",
                        config.get("belege", "source_folder"),
                        config.get("belege", "processed_folder"),
                        Path(config.get("belege", "output_folder"))))
    return jobs


def get_password(config, username: str, logger) -> str:
    """
    Holt das IMAP-Passwort: zuerst aus dem Windows-Schlüsselbund (Dienst 'email_archiver',
    Benutzer = IMAP-Benutzername, angelegt mit set_credentials.py), sonst aus [imap] password.

    Args:
        config: Geladene Konfiguration
        username (str): IMAP-Benutzername
        logger: ExtendedLogger-Instanz

    Returns:
        str: Passwort

    Raises:
        ValueError: Wenn weder Schlüsselbund noch INI ein Passwort liefern
    """
    try:
        import keyring
        password = keyring.get_password(KEYRING_SERVICE, username)
    except ImportError:
        password = None
    if password:
        logger.info("IMAP-Passwort aus dem Windows-Schlüsselbund")
        return password
    password = config.get("imap", "password", fallback="").strip()
    if password:
        logger.info("IMAP-Passwort aus config.ini")
        return password
    raise ValueError(
        f"Kein IMAP-Passwort: weder im Schlüsselbund (Dienst '{KEYRING_SERVICE}', Konto "
        f"{os.environ.get('USERNAME')}) noch in config.ini. Abhilfe: set_credentials.py"
    )


def acquire_lock(lock_path: Path, wait_seconds: int, stale_minutes: int, logger) -> bool:
    """
    Belegt die gemeinsame Sperrdatei (exklusiv anlegen), damit nie zwei Archiver
    (z. B. Task auf dem HauServer und Handstart auf AHMain) gleichzeitig dieselben
    IMAP-Ordner verarbeiten.

    Ist die Sperre belegt, wird bis zu wait_seconds gewartet. Eine Sperre, die älter als
    stale_minutes ist, gilt als verwaist (abgestürzter Lauf) und wird entfernt.

    Args:
        lock_path (Path): Sperrdatei (auf dem HauServer lokal, auf AHMain per UNC)
        wait_seconds (int): Maximale Wartezeit bei belegter Sperre
        stale_minutes (int): Alter, ab dem eine Sperre als verwaist gilt
        logger: ExtendedLogger-Instanz

    Returns:
        bool: True = Sperre belegt (Lauf darf starten), False = Sperre blieb belegt
    """
    deadline = time.monotonic() + wait_seconds
    waited = False
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{socket.gethostname()} {os.getpid()} {datetime.now():%Y-%m-%d %H:%M:%S}".encode())
            os.close(fd)
            logger.info(f"Sperre belegt: {lock_path}")
            return True
        except FileExistsError:
            try:
                age = time.time() - lock_path.stat().st_mtime
                holder = lock_path.read_text(encoding="utf-8", errors="replace").strip()
            except FileNotFoundError:
                continue  # gerade freigegeben
            if age > stale_minutes * 60:
                logger.warning(f"Verwaiste Sperre entfernt ({holder}, {age / 60:.0f} Min. alt)")
                lock_path.unlink(missing_ok=True)
                continue
            if not waited:
                logger.info(f"Sperre belegt ({holder}), warte bis zu {wait_seconds} s ...")
                waited = True
            if time.monotonic() > deadline:
                logger.warning(f"Sperre weiterhin belegt ({holder}): Lauf übersprungen")
                return False
            time.sleep(2)


def release_lock(lock_path: Path) -> None:
    """Gibt die Sperrdatei frei."""
    lock_path.unlink(missing_ok=True)


def main() -> None:
    """
    Hauptfunktion: Konfiguration laden, IMAP verbinden, E-Mails verarbeiten, zusammenfassen.
    """
    parser = argparse.ArgumentParser(description="E-Mails per IMAP als PDF archivieren")
    parser.add_argument("--dry-run", action="store_true",
                        help="nur auflisten: kein PDF erzeugen, nichts verschieben")
    args = parser.parse_args()

    # --- Logging initialisieren (eine Datei pro Monat, angehängt) ---
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"email_archiver_{datetime.now():%Y-%m}.log"
    logger = create_extended_logger(str(log_file), screen_output=True, script_name="email_archiver")

    logger.info("=" * 60)
    logger.info("email_archiver gestartet" + (" (DryRun)" if args.dry_run else ""))
    logger.info("=" * 60)

    # --- Konfiguration laden ---
    try:
        config = load_config("config/config.ini", logger)
        server = config.get("imap", "server")
        port = config.getint("imap", "port")
        username = config.get("imap", "username")
        jobs = read_jobs(config)
        password = get_password(config, username, logger)
        lock_file = config.get("run", "lock_file", fallback="").strip()
        lock_wait = config.getint("run", "lock_wait_seconds", fallback=60)
        lock_stale = config.getint("run", "lock_stale_minutes", fallback=10)
    except Exception as exc:
        logger.error(f"Konfiguration: {exc}")
        sys.exit(1)

    # --- Ausgabeordner sicherstellen ---
    for job in jobs:
        ensure_output_folder(str(job.output_folder))

    # --- Gemeinsame Sperre (optional, [run] lock_file) ---
    lock_path = Path(lock_file) if lock_file else None
    if lock_path and not acquire_lock(lock_path, lock_wait, lock_stale, logger):
        return  # anderer Archiver läuft gerade: kein Fehler (Exit 0)

    # --- IMAP-Verbindung herstellen ---
    client = None
    success_count = 0
    error_count = 0
    try:
        logger.info(f"Verbinde mit {server}:{port} als {username} ...")
        client = imap.connect(server, port, username, password)

        # --- E-Mails je Auftrag verarbeiten ---
        for job in jobs:
            ok, err = process_emails(client, job, logger, dry_run=args.dry_run)
            success_count += ok
            error_count += err

    except Exception as exc:
        logger.error(f"Kritischer Fehler: {exc}")
        sys.exit(1)

    finally:
        if client is not None:
            imap.disconnect(client)
        if lock_path:
            release_lock(lock_path)

    # --- Abschluss-Zusammenfassung ---
    logger.info("=" * 60)
    logger.info(f"Fertig -- Erfolgreich: {success_count}, Fehler: {error_count}")
    logger.info("=" * 60)

    if error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
