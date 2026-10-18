"""
converter.py — E-Mail-zu-PDF-Konvertierung für email_archiver

Verwendet Playwright (Headless Chromium) für HTML → PDF.
Externe URLs werden auf Netzwerkebene blockiert (Datenschutz/Tracking-Schutz).
cid:-Inline-Bilder werden als data:-URIs eingebettet und vom Browser gerendert.
Anhänge werden via pikepdf als EmbeddedFile in das erzeugte PDF eingefügt.

Stellt bereit:
  - convert_and_save() : Vollständige Konvertierung einer E-Mail in eine PDF-Datei
"""

import atexit
import base64
import html as html_module
import logging
import re
import urllib.error
import urllib.request
from email.message import Message
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pikepdf
from pikepdf import AttachedFileSpec
from playwright.sync_api import sync_playwright, Browser, Playwright

from utils import decode_mime_header

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Browser-Lifecycle: einmaliger Start, atexit-Cleanup
# ---------------------------------------------------------------------------

_pw: Playwright | None = None
_browser: Browser | None = None


def _get_browser() -> Browser:
    """Gibt den gemeinsam genutzten Chromium-Browser zurück (lazy start)."""
    global _pw, _browser
    if _browser is None:
        _pw = sync_playwright().start()
        _browser = _pw.chromium.launch()
        atexit.register(_shutdown_browser)
        logger.debug("Playwright Chromium gestartet.")
    return _browser


def _shutdown_browser() -> None:
    """Fährt den Browser beim Prozessende herunter (atexit-Handler)."""
    global _pw, _browser
    if _browser is not None:
        try:
            _browser.close()
            _pw.stop()
        except Exception:
            pass
        _browser = None
        _pw = None
        logger.debug("Playwright Chromium gestoppt.")


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
    cid:-Referenzen im HTML, damit der Browser die Bilder rendern kann.
    data:-URIs werden nicht über das Netzwerk geladen und unterliegen damit
    nicht der externen URL-Blockierung.

    Args:
        msg (Message): Geparste E-Mail (alle MIME-Parts werden durchsucht)
        html (str): HTML-String mit potentiellen cid:-Referenzen

    Returns:
        str: HTML-String mit aufgelösten data:-URIs anstelle von cid:-Referenzen
    """
    cid_map: dict[str, str] = {}
    for part in msg.walk():
        content_id = part.get("Content-ID", "").strip()
        if not content_id:
            continue
        content_id = content_id.strip("<>")
        data = part.get_payload(decode=True)
        if not data:
            continue
        mime_type = part.get_content_type()
        encoded = base64.b64encode(data).decode("ascii")
        cid_map[content_id] = f"data:{mime_type};base64,{encoded}"

    if not cid_map:
        return html

    def replace_cid(match: re.Match) -> str:
        cid = match.group(1)
        return cid_map.get(cid, match.group(0))

    return re.sub(r'cid:([^\s"\']+)', replace_cid, html, flags=re.IGNORECASE)


# ---------------------------------------------------------------------------
# Externe Bilder herunterladen und einbetten
# ---------------------------------------------------------------------------

def _resolve_external_images(html: str) -> str:
    """
    Lädt extern referenzierte Bilder herunter und bettet sie als data:-URIs ein.

    Behandelt:
    - src="https://..."-Attribute in HTML-Tags (img, input usw.)
    - url(...)-Referenzen in CSS (sowohl in <style>-Blöcken als auch in
      inline style-Attributen), z.B. background-image: url('https://...')

    Nicht ladbare Ressourcen bleiben unverändert. Gleiche URLs werden nur
    einmal heruntergeladen (Cache).

    Args:
        html (str): HTML-String mit potentiellen externen Bild-URLs

    Returns:
        str: HTML-String mit eingebetteten Ressourcen als data:-URIs
    """
    _cache: dict[str, str | None] = {}

    def _download(url: str) -> str | None:
        if url in _cache:
            return _cache[url]
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                mime = resp.headers.get_content_type() or "image/jpeg"
                data = resp.read()
            encoded = base64.b64encode(data).decode("ascii")
            result = f"data:{mime};base64,{encoded}"
        except Exception as exc:
            logger.debug("Externe Ressource nicht ladbar (%s): %s", url, exc)
            result = None
        _cache[url] = result
        return result

    def _replace_src(m: re.Match) -> str:
        quote, url = m.group(1), m.group(2)
        data_uri = _download(url)
        return f"src={quote}{data_uri}{quote}" if data_uri else m.group(0)

    def _replace_css_url(m: re.Match) -> str:
        url = m.group(1)
        data_uri = _download(url)
        return f"url('{data_uri}')" if data_uri else m.group(0)

    # src-Attribute in HTML-Tags
    html = re.sub(r'src=(["\'])(https?://[^"\']+)\1', _replace_src, html)
    # url()-Referenzen in CSS (style-Attribute und <style>-Blöcke)
    html = re.sub(r'url\(["\']?(https?://[^"\')\s]+)["\']?\)', _replace_css_url, html)
    return html


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
        escaped = html_module.escape(plain_text)
        return (
            f'<pre style="white-space: pre-wrap; word-wrap: break-word; '
            f'font-family: monospace; font-size: 10pt;">{escaped}</pre>'
        )

    logger.warning("Kein Body-Part in der E-Mail gefunden.")
    return "<p><em>(Kein Inhalt)</em></p>"


# ---------------------------------------------------------------------------
# Anhänge extrahieren und einbetten
# ---------------------------------------------------------------------------

def _extract_attachments(msg: Message) -> list[tuple[str, bytes]]:
    """
    Extrahiert alle Dateianhänge aus der E-Mail.

    Anhänge werden anhand von Content-Disposition: attachment oder
    einem vorhandenen Dateinamen erkannt. Inline-Bilder (Content-ID)
    werden übersprungen, da sie bereits als data:-URI im HTML-Body gerendert sind.

    Args:
        msg (Message): Geparste E-Mail

    Returns:
        list[tuple[str, bytes]]: Liste von (Dateiname, Rohdaten).
    """
    attachments = []
    if not msg.is_multipart():
        return attachments

    for part in msg.walk():
        content_type = part.get_content_type()
        disposition = part.get("Content-Disposition", "")
        filename = part.get_filename()

        if "attachment" not in disposition and not filename:
            continue
        if content_type.startswith("multipart/"):
            continue
        if part.get("Content-ID"):
            continue

        if filename:
            filename = decode_mime_header(filename)

        data = part.get_payload(decode=True)
        if data and filename:
            attachments.append((filename, data))
            logger.debug(f"Anhang gefunden: {filename} ({len(data)} Bytes)")

    return attachments


def _embed_attachments(pdf_path: Path, attachments: list[tuple[str, bytes]]) -> None:
    """
    Bettet Dateianhänge als EmbeddedFile in eine bestehende PDF-Datei ein.

    Die eingebetteten Dateien sind im Büroklammer-Panel von Adobe Acrobat
    und PDF-XChange sichtbar und können von dort geöffnet/gespeichert werden.

    Args:
        pdf_path (Path): Pfad zur bestehenden PDF-Datei (wird überschrieben)
        attachments (list[tuple[str, bytes]]): Liste von (Dateiname, Rohdaten)
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
      1. Metadaten aus E-Mail-Headern extrahieren
      2. HTML-Body extrahieren
      3. cid:-Inline-Bilder als data:-URIs einbetten
      3b. Externe Bilder + CSS-Hintergrundbilder (http/https) herunterladen und als data:-URIs einbetten
      4. Metadaten-Header-Block (Von/An/Betreff/Gesendet) einfügen
      5. HTML → PDF via Playwright/Chromium
         - Externe URLs (http/https) werden auf Netzwerkebene blockiert
      6. PDF auf Disk speichern
      7. Anhänge via pikepdf als EmbeddedFile einbetten

    Args:
        msg (Message): Geparste E-Mail (email.message.Message)
        pdf_path (Path): Zielpfad für die PDF-Datei

    Raises:
        Exception: Weiterleitung von Playwright- oder pikepdf-Fehlern.
                   Der Aufrufer (main.py) fängt diese ab und behandelt sie pro E-Mail.
    """
    # --- Metadaten aus E-Mail-Headern ---
    subject   = decode_mime_header(msg.get("Subject", "(kein Betreff)"))
    from_addr = decode_mime_header(msg.get("From", ""))
    to_addr   = decode_mime_header(msg.get("To", ""))
    date_str  = msg.get("Date", "")
    date_german = _format_date_german(date_str)

    # --- Body extrahieren + cid:-Bilder auflösen + externe Bilder einbetten ---
    body_html = _extract_body(msg)
    body_html = _resolve_cid_images(msg, body_html)
    body_html = _resolve_external_images(body_html)

    # --- Metadaten-Header-Block als HTML ---
    # Jede Zeile als eigenes <div> statt <br>, damit Email-CSS den Zeilenumbruch
    # nicht unterdrücken kann (z.B. white-space:nowrap oder display:table-cell).
    # Der id="ea-meta" wird in print_css mit !important-Regeln abgesichert.
    meta_block = (
        '<div id="ea-meta" style="'
        "border-bottom: 2px solid #cccccc;"
        "margin-bottom: 1.2em;"
        "padding-bottom: 0.8em;"
        "font-family: Arial, Helvetica, sans-serif;"
        "font-size: 9pt;"
        'color: #444444;">'
        f'<div><strong>Von:</strong> {html_module.escape(from_addr)}</div>'
        f'<div><strong>An:</strong> {html_module.escape(to_addr)}</div>'
        f'<div><strong>Betreff:</strong> {html_module.escape(subject)}</div>'
        f'<div><strong>Gesendet:</strong> {html_module.escape(date_german)}</div>'
        "</div>"
    )

    # --- Druck-CSS ---
    print_css = (
        "<style>"
        "@media print { body { margin: 0; } }"
        "body { font-family: Arial, Helvetica, sans-serif; font-size: 10pt; }"
        "a { color: #1155CC; }"
        "img { max-width: 100%; height: auto; }"
        # Outlook-HTML definiert benannte CSS-Seiten (page: WordSection1).
        # Chromium fügt beim Übergang zu einer benannten Seite einen Seitenumbruch
        # ein — direkt nach dem Meta-Header. Wird hier auf auto zurückgesetzt.
        "div[class*='WordSection'] { page: auto !important; }"
        # Meta-Header: ID-basierte !important-Regeln schützen vor Email-CSS-Overrides
        # (z.B. display:table-cell, white-space:nowrap, font-size:0 auf divs).
        "#ea-meta {"
        " display: block !important;"
        " visibility: visible !important;"
        " border-bottom: 2px solid #cccccc !important;"
        " margin: 0 0 1.2em 0 !important;"
        " padding: 0 0 0.8em 0 !important;"
        " font-family: Arial, Helvetica, sans-serif !important;"
        " font-size: 9pt !important;"
        " color: #444444 !important;"
        " background: none !important;"
        " width: auto !important;"
        " float: none !important;"
        " position: static !important;"
        " white-space: normal !important;"
        "}"
        "#ea-meta > div {"
        " display: block !important;"
        " visibility: visible !important;"
        " font-size: 9pt !important;"
        " color: #444444 !important;"
        " line-height: 1.5 !important;"
        " margin: 1px 0 !important;"
        " padding: 0 !important;"
        " white-space: normal !important;"
        " height: auto !important;"
        " overflow: visible !important;"
        " width: auto !important;"
        "}"
        "</style>"
    )

    # --- Vollständiges HTML-Dokument zusammensetzen ---
    if re.search(r"<body[^>]*>", body_html, re.IGNORECASE):
        if re.search(r"</head>", body_html, re.IGNORECASE):
            full_html = re.sub(
                r"(</head>)", print_css + r"\1", body_html, count=1, flags=re.IGNORECASE
            )
        else:
            full_html = print_css + body_html
        full_html = re.sub(
            r"(<body[^>]*>)", r"\1" + meta_block, full_html, count=1, flags=re.IGNORECASE
        )
    else:
        full_html = (
            "<!DOCTYPE html>"
            '<html><head><meta charset="utf-8">'
            f"{print_css}</head><body>{meta_block}{body_html}</body></html>"
        )

    # --- HTML → PDF via Playwright ---
    browser = _get_browser()
    page = browser.new_page()
    try:
        # Externe URLs auf Netzwerkebene blockieren (Datenschutz/Tracking-Schutz).
        # data:-URIs werden vom Browser intern verarbeitet und gehen nicht durch
        # den Route-Handler — sie werden also korrekt gerendert.
        page.route(
            "**/*",
            lambda route: (
                route.abort()
                if route.request.url.startswith(("http://", "https://", "//"))
                else route.continue_()
            ),
        )
        page.set_content(full_html, wait_until="domcontentloaded")
        pdf_bytes = page.pdf(
            format="A4",
            margin={"top": "1cm", "bottom": "1cm", "left": "1.5cm", "right": "1.5cm"},
            print_background=True,
        )
    finally:
        page.close()

    pdf_path.write_bytes(pdf_bytes)
    logger.debug(f"PDF geschrieben: {pdf_path.name} ({len(pdf_bytes)} Bytes)")

    # --- Anhänge einbetten ---
    attachments = _extract_attachments(msg)
    if attachments:
        _embed_attachments(pdf_path, attachments)
        logger.debug(f"{len(attachments)} Anhang/Anhänge in PDF eingebettet.")
