"""
utils.py — Hilfsfunktionen für email_archiver

Stellt bereit:
  - sanitize_filename()   : Absendernamen für Dateinamen bereinigen
  - decode_mime_header()  : MIME-kodierte Header-Werte dekodieren
  - build_pdf_filename()  : PDF-Dateipfad nach Namenskonvention erzeugen
"""

import re
import email.utils
from email.header import decode_header, make_header
from pathlib import Path
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)

BERLIN_TZ = ZoneInfo("Europe/Berlin")
MAX_SENDER_LEN = 60


def decode_mime_header(header_value: str) -> str:
    """
    Dekodiert einen MIME-kodierten Header-Wert (z.B. =?utf-8?B?...?= oder =?iso-8859-1?Q?...?=).

    Args:
        header_value (str): Roher Header-Wert aus der E-Mail

    Returns:
        str: Dekodierter, lesbarer String. Bei Fehler wird der Rohwert zurückgegeben.
    """
    if not header_value:
        return ""
    try:
        return str(make_header(decode_header(header_value)))
    except Exception:
        return header_value


def sanitize_filename(name: str) -> str:
    """
    Bereinigt einen String für die Verwendung als Dateinamensteil.

    Regeln:
      - Alles außer Buchstaben (inkl. Unicode), Ziffern, Bindestrich und Punkt → Unterstrich
      - Mehrfache aufeinanderfolgende Unterstriche werden zusammengefasst
      - Führende und abschließende Unterstriche werden entfernt
      - Ergebnis wird auf MAX_SENDER_LEN Zeichen gekürzt

    Args:
        name (str): Ursprünglicher Name (z.B. Display Name oder E-Mail-Adresse)

    Returns:
        str: Bereinigter Dateinamen-Teil, maximal MAX_SENDER_LEN Zeichen lang.
             Leerer String wenn der Name nach Bereinigung leer ist.
    """
    # Alles außer Unicode-Buchstaben, Ziffern, Bindestrich und Punkt durch Unterstrich ersetzen
    sanitized = re.sub(r'[^\w\-.]', '_', name, flags=re.UNICODE)
    # Mehrfache Unterstriche zusammenfassen
    sanitized = re.sub(r'_+', '_', sanitized)
    # Führende/abschließende Unterstriche entfernen
    sanitized = sanitized.strip('_')
    # Auf maximale Länge kürzen
    return sanitized[:MAX_SENDER_LEN]


def build_pdf_filename(date_str: str, from_str: str, output_folder: Path) -> Path:
    """
    Erzeugt den vollständigen PDF-Dateipfad nach der Namenskonvention.

    Format: YYYY-MM-DD_HH-MM_Absender.pdf
      - Datum/Uhrzeit aus dem Date-Header der E-Mail, umgerechnet auf Europe/Berlin
      - Absender: zuerst Display Name, sonst E-Mail-Adresse
      - Sonderzeichen/Leerzeichen/Umlaute → Unterstriche
      - Bei Namenskollision: Suffix _2, _3, ... anfügen

    Args:
        date_str (str): Wert des Date-Headers der E-Mail (RFC 2822)
        from_str (str): Wert des From-Headers der E-Mail (ggf. MIME-kodiert)
        output_folder (Path): Zielverzeichnis für die PDF-Datei

    Returns:
        Path: Vollständiger, noch nicht existierender Dateipfad

    Raises:
        ValueError: Wenn der Date-Header nicht geparst werden kann
    """
    # Datum parsen und in Berliner Lokalzeit umrechnen
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        dt_berlin = dt.astimezone(BERLIN_TZ)
    except Exception as exc:
        raise ValueError(f"Date-Header konnte nicht geparst werden: {date_str!r}") from exc

    date_part = dt_berlin.strftime("%Y-%m-%d_%H-%M")

    # Absender: Display Name bevorzugt, sonst E-Mail-Adresse
    from_decoded = decode_mime_header(from_str)
    realname, addr = email.utils.parseaddr(from_decoded)
    sender_raw = realname.strip() if realname.strip() else addr.strip()
    sender_part = sanitize_filename(sender_raw) or "unbekannt"

    base_name = f"{date_part}_{sender_part}"
    candidate = output_folder / f"{base_name}.pdf"

    if not candidate.exists():
        return candidate

    # Kollisionsauflösung mit numerischem Suffix
    counter = 2
    while True:
        candidate = output_folder / f"{base_name}_{counter}.pdf"
        if not candidate.exists():
            return candidate
        counter += 1
