"""
converter.py — E-Mail-zu-PDF-Konvertierung für email_archiver

Verarbeitungsablauf:
  1. E-Mail-Body extrahieren (HTML bevorzugt, Fallback: text/plain → HTML-Wrapper)
  2. E-Mail-Metadaten (Von, An, Betreff, Gesendet) als sichtbaren Header-Block einbetten
  3. HTML → PDF via xhtml2pdf (externe URLs werden blockiert)
  4. Anhänge aus der E-Mail extrahieren
  5. Anhänge als EmbeddedFile in das PDF einbetten via pikepdf
     (sichtbar im Büroklammer-Panel in Adobe Acrobat, PDF-XChange etc.)

Stellt bereit:
  - convert_and_save() : Vollständige Konvertierung einer E-Mail in eine PDF-Datei
"""

import base64
import html as html_module
import io
import logging
import re
from email.message import Message
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pikepdf
from pikepdf import AttachedFileSpec
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xhtml2pdf import pisa

from utils import decode_mime_header

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TrueType-Fonts registrieren (Unicode-Unterstützung für Umlaute etc.)
# ---------------------------------------------------------------------------

def _register_unicode_fonts() -> None:
    """
    Registriert Arial als TrueType-Font bei reportlab.

    Ohne TTF-Font verwendet reportlab intern Helvetica (Type 1), das nur den
    Latin-1-Zeichensatz unterstützt. Umlaute und andere Unicode-Zeichen
    werden dann als Byte-Sequenzen in den PDF-Stream geschrieben und nicht
    korrekt gerendert. Arial aus den Windows-Systemfonts unterstützt den
    vollen Unicode-Bereich.
    """
    fonts_dir = Path("C:/Windows/Fonts")
    font_map = {
        "Arial":           "arial.ttf",
        "Arial-Bold":      "arialbd.ttf",
        "Arial-Italic":    "ariali.ttf",
        "Arial-BoldItalic":"arialbi.ttf",
    }
    for name, filename in font_map.items():
        font_path = fonts_dir / filename
        if font_path.exists():
            try:
                pdfmetrics.registerFont(TTFont(name, str(font_path)))
            except Exception as exc:
                logger.warning(f"Font '{name}' konnte nicht registriert werden: {exc}")

_register_unicode_fonts()


# ---------------------------------------------------------------------------
# Link-Callback: externe Ressourcen blockieren (Datenschutz, Tracking-Schutz)
# ---------------------------------------------------------------------------

def _block_external_urls(uri: str, rel: str) -> str | None:
    """
    xhtml2pdf link_callback, der externe URLs blockiert.

    Wird von xhtml2pdf aufgerufen, wenn das HTML externe Ressourcen referenziert
    (Bilder, Stylesheets etc.). Externe URLs (http/https) werden blockiert,
    um Tracking-Pixel und externe Ressourcen in HTML-E-Mails zu unterdrücken.
    data:-URIs werden direkt von xhtml2pdf verarbeitet und rufen diesen
    Callback nicht auf.

    Args:
        uri (str): Die referenzierte URI
        rel (str): Relativer Pfad (von xhtml2pdf übergeben)

    Returns:
        str | None: None blockiert die Ressource, sonst der lokale Pfad
    """
    if uri.startswith(("http://", "https://", "//")):
        logger.debug(f"Externe URL blockiert (Datenschutz): {uri}")
        return None
    return uri


# ---------------------------------------------------------------------------
# Datum in deutsches Langformat konvertieren
# ---------------------------------------------------------------------------

_GERMAN_MONTHS = {
    1: "Januar", 2: "Februar", 3: "März", 4: "April",
    5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
    9: "September", 10: "Oktober", 11: "November", 12: "Dezember"
}


def _format_date_german(date_str: str) -> str:
    """Konvertiert einen RFC-2822-Datums-String in deutsches Langformat (z.B. '15. Juni 2026')."""
    try:
        dt = parsedate_to_datetime(date_str).astimezone(ZoneInfo("Europe/Berlin"))
        return f"{dt.day}. {_GERMAN_MONTHS[dt.month]} {dt.year}"
    except Exception:
        return date_str


# ---------------------------------------------------------------------------
# cid:-Bilder auflösen (multipart/related Inline-Bilder)
# ---------------------------------------------------------------------------

def _resolve_cid_images(msg: Message, html: str) -> str:
    """
    Ersetzt cid:-Referenzen in HTML durch base64-kodierte data:-URIs.

    In multipart/related E-Mails werden Inline-Bilder als separate MIME-Parts
    gespeichert und im HTML via src="cid:<content-id>" referenziert. Diese
    Funktion sucht alle solchen Parts, kodiert sie als base64 und ersetzt die
    cid:-Referenzen im HTML, damit xhtml2pdf die Bilder rendern kann.

    Args:
        msg (Message): Geparste E-Mail (alle MIME-Parts werden durchsucht)
        html (str): HTML-String mit potentiellen cid:-Referenzen

    Returns:
        str: HTML-String mit aufgelösten data:-URIs anstelle von cid:-Referenzen
    """
    # Content-ID → data-URI Mapping aufbauen
    cid_map: dict[str, str] = {}
    for part in msg.walk():
        content_id = part.get("Content-ID", "").strip()
        if not content_id:
            continue
        # Angle brackets entfernen: <image001.png@xxx> → image001.png@xxx
        content_id = content_id.strip("<>")
        data = part.get_payload(decode=True)
        if not data:
            continue
        mime_type = part.get_content_type()
        encoded = base64.b64encode(data).decode("ascii")
        cid_map[content_id] = f"data:{mime_type};base64,{encoded}"

    if not cid_map:
        return html

    # cid:xxx → data:image/...;base64,... ersetzen (case-insensitive)
    def replace_cid(match: re.Match) -> str:
        cid = match.group(1)
        return cid_map.get(cid, match.group(0))

    return re.sub(r'cid:([^\s"\']+)', replace_cid, html, flags=re.IGNORECASE)


# ---------------------------------------------------------------------------
# Body-Extraktion
# ---------------------------------------------------------------------------

def _extract_body(msg: Message) -> str:
    """
    Extrahiert den E-Mail-Body als HTML-String.

    Bevorzugt den text/html-Part. Fällt auf text/plain zurück, der dann
    in einen einfachen HTML-Wrapper eingebettet wird. Parts mit
    Content-Disposition: attachment werden übersprungen.

    Args:
        msg (Message): Geparste E-Mail (email.message.Message)

    Returns:
        str: HTML-String des E-Mail-Bodys. Gibt ein Minimal-HTML zurück,
             wenn kein Body gefunden wird.
    """
    html_part = None
    text_part = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = part.get("Content-Disposition", "")
            # Anhänge überspringen
            if "attachment" in disposition:
                continue
            if content_type == "text/html" and html_part is None:
                html_part = part
            elif content_type == "text/plain" and text_part is None:
                text_part = part
    else:
        content_type = msg.get_content_type()
        if content_type == "text/html":
            html_part = msg
        elif content_type == "text/plain":
            text_part = msg

    if html_part is not None:
        charset = html_part.get_content_charset() or "utf-8"
        raw = html_part.get_payload(decode=True)
        return raw.decode(charset, errors="replace")

    if text_part is not None:
        charset = text_part.get_content_charset() or "utf-8"
        raw = text_part.get_payload(decode=True)
        plain_text = raw.decode(charset, errors="replace")
        # Plain-Text HTML-sicher machen und in <pre> wrappen
        escaped = html_module.escape(plain_text)
        return (
            f'<pre style="white-space: pre-wrap; word-wrap: break-word; '
            f'font-family: monospace; font-size: 10pt;">{escaped}</pre>'
        )

    logger.warning("Kein Body-Part in der E-Mail gefunden.")
    return "<p><em>(Kein Inhalt)</em></p>"


# ---------------------------------------------------------------------------
# Anhänge extrahieren
# ---------------------------------------------------------------------------

def _extract_attachments(msg: Message) -> list[tuple[str, bytes]]:
    """
    Extrahiert alle Dateianhänge aus der E-Mail.

    Anhänge werden anhand von Content-Disposition: attachment oder
    einem vorhandenen Dateinamen (get_filename()) erkannt.
    text/* und multipart/* ohne Dateinamen werden als Body-Parts behandelt
    und nicht extrahiert.

    Args:
        msg (Message): Geparste E-Mail

    Returns:
        list[tuple[str, bytes]]: Liste von (Dateiname, Rohdaten).
                                 Leere Liste wenn keine Anhänge vorhanden.
    """
    attachments = []

    if not msg.is_multipart():
        return attachments

    for part in msg.walk():
        content_type = part.get_content_type()
        disposition = part.get("Content-Disposition", "")
        filename = part.get_filename()

        # Body-Parts ohne explizite Anhang-Disposition überspringen
        if "attachment" not in disposition and not filename:
            continue
        # multipart/* enthält keine Nutzdaten
        if content_type.startswith("multipart/"):
            continue

        if filename:
            filename = decode_mime_header(filename)

        data = part.get_payload(decode=True)
        if data and filename:
            attachments.append((filename, data))
            logger.debug(f"Anhang gefunden: {filename} ({len(data)} Bytes)")

    return attachments


# ---------------------------------------------------------------------------
# Anhänge in PDF einbetten
# ---------------------------------------------------------------------------

def _embed_attachments(pdf_path: Path, attachments: list[tuple[str, bytes]]) -> None:
    """
    Bettet Dateianhänge als EmbeddedFile in eine bestehende PDF-Datei ein.

    Die eingebetteten Dateien sind im Büroklammer-Panel von Adobe Acrobat
    und PDF-XChange sichtbar und können von dort geöffnet/gespeichert werden.

    Args:
        pdf_path (Path): Pfad zur bestehenden PDF-Datei (wird überschrieben)
        attachments (list[tuple[str, bytes]]): Liste von (Dateiname, Rohdaten)

    Raises:
        pikepdf.PdfError: Bei Fehler beim Öffnen oder Speichern der PDF
    """
    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        for filename, data in attachments:
            filespec = AttachedFileSpec(pdf, data, description=filename, filename=filename)
            pdf.attachments[filename] = filespec
        pdf.save(pdf_path)


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------

def convert_and_save(msg: Message, pdf_path: Path) -> None:
    """
    Konvertiert eine E-Mail vollständig in eine PDF-Datei mit eingebetteten Anhängen.

    Ablauf:
      1. Body (HTML oder Plain-Text) extrahieren
      2. HTML-Dokument mit Metadaten-Header (Von, Betreff, Datum) aufbauen
      3. HTML → PDF via xhtml2pdf (externe URLs werden blockiert)
      4. PDF auf Disk speichern
      5. Anhänge extrahieren und via pikepdf in das PDF einbetten

    Args:
        msg (Message): Geparste E-Mail (email.message.Message)
        pdf_path (Path): Zielpfad für die PDF-Datei (Elternverzeichnis muss existieren)

    Raises:
        RuntimeError: Wenn xhtml2pdf die PDF-Konvertierung meldet
        Exception: Weiterleitung von pikepdf-Fehlern.
                   Der Aufrufer (main.py) fängt diese ab und behandelt sie pro E-Mail.
    """
    # --- Metadaten aus E-Mail-Headern ---
    subject = decode_mime_header(msg.get("Subject", "(kein Betreff)"))
    from_addr = decode_mime_header(msg.get("From", ""))
    to_addr = decode_mime_header(msg.get("To", ""))
    date_str = msg.get("Date", "")
    date_german = _format_date_german(date_str)

    # --- Body extrahieren und cid:-Bilder auflösen ---
    body_html = _extract_body(msg)
    body_html = _resolve_cid_images(msg, body_html)

    # --- Metadaten-Header-Block als HTML ---
    meta_block = (
        '<div style="'
        "border-bottom: 2px solid #cccccc;"
        "margin-bottom: 1.2em;"
        "padding-bottom: 0.8em;"
        "font-family: Arial, Helvetica, sans-serif;"
        "font-size: 9pt;"
        'color: #444444;">'
        f"<strong>Von:</strong> {html_module.escape(from_addr)}<br>"
        f"<strong>An:</strong> {html_module.escape(to_addr)}<br>"
        f"<strong>Betreff:</strong> {html_module.escape(subject)}<br>"
        f"<strong>Gesendet:</strong> {html_module.escape(date_german)}"
        "</div>"
    )

    # --- CSS-Block mit Unicode-fähigem Font ---
    # Arial wurde beim Modulstart via pdfmetrics.registerFont(TTFont(...)) registriert.
    # xhtml2pdf verwendet den registrierten TTF-Font wenn font-family: Arial angegeben wird.
    # Kein @font-face nötig (Windows-Pfade würden von xhtml2pdf als URL fehlinterpretiert).
    unicode_css = (
        "body { font-family: Arial, sans-serif; font-size: 10pt; }"
        "a { color: #1155CC; }"
        "img { max-width: 100%; height: auto; }"
    )

    # --- Vollständiges HTML-Dokument zusammensetzen ---
    # Wenn der Body bereits ein <body>-Tag enthält, meta_block dahinter einfügen
    # und unicode_css in den <head> injizieren.
    # Andernfalls komplettes Dokument-Gerüst aufbauen.
    if re.search(r"<body[^>]*>", body_html, re.IGNORECASE):
        # unicode_css vor dem schließenden </head> oder vor <body> einfügen
        style_tag = f"<style>{unicode_css}</style>"
        if re.search(r"</head>", body_html, re.IGNORECASE):
            full_html = re.sub(
                r"(</head>)", style_tag + r"\1", body_html, count=1, flags=re.IGNORECASE
            )
        else:
            full_html = style_tag + body_html
        full_html = re.sub(
            r"(<body[^>]*>)",
            r"\1" + meta_block,
            full_html,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        full_html = (
            "<!DOCTYPE html>"
            '<html><head><meta charset="utf-8">'
            f"<style>{unicode_css}</style>"
            f"</head><body>{meta_block}{body_html}</body></html>"
        )

    # --- HTML → PDF via xhtml2pdf ---
    # Als Unicode-String übergeben (nicht als Bytes), damit xhtml2pdf
    # Unicode-Zeichen korrekt auf WinAnsi-Codes mappt. Bei Übergabe als
    # UTF-8-Bytes wurden die Multi-Byte-Sequenzen direkt in den PDF-Stream
    # geschrieben, was zu kaputten Umlauten führt.
    pdf_buffer = io.BytesIO()
    status = pisa.CreatePDF(
        full_html,
        dest=pdf_buffer,
        link_callback=_block_external_urls,
    )
    if status.err:
        raise RuntimeError(f"xhtml2pdf Konvertierungsfehler (Code {status.err})")

    pdf_bytes = pdf_buffer.getvalue()
    pdf_path.write_bytes(pdf_bytes)
    logger.debug(f"PDF geschrieben: {pdf_path.name} ({len(pdf_bytes)} Bytes)")

    # --- Anhänge extrahieren und einbetten ---
    attachments = _extract_attachments(msg)
    if attachments:
        _embed_attachments(pdf_path, attachments)
        logger.debug(f"{len(attachments)} Anhang/Anhänge in PDF eingebettet.")
