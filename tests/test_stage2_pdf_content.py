"""
Stufe-2-Tests: PDF-Metadaten-Header und Kompatibilität mit correspondence_cleanup

Prüft, dass convert_and_save() korrekte Von/An/Betreff/Gesendet-Felder
in das PDF schreibt und dass die Regex-Muster aus correspondence_cleanup_1_email.py
darauf matchen.

Voraussetzung (einmalig):
    pip install PyPDF2

Ausführen:
    python tests/test_stage2_pdf_content.py
    oder: python -m pytest tests/test_stage2_pdf_content.py -v
"""

import os
import re
import sys
import tempfile
import unittest
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import PyPDF2

# Projektwurzel als Arbeitsverzeichnis setzen (Font-Pfade etc.)
_project_root = Path(__file__).parent.parent
os.chdir(_project_root)
sys.path.insert(0, str(_project_root / "src"))

from converter import convert_and_save


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def extract_pdf_text(pdf_path: Path) -> str:
    """Extrahiert den Volltext eines PDFs mit PyPDF2 (wie correspondence_cleanup)."""
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        return "\n".join(page.extract_text() or "" for page in reader.pages)


def make_simple_email(
    from_: str = "sender@example.com",
    to_: str = "empfaenger@example.com",
    subject: str = "Testbetreff",
    date_: str = "Thu, 11 Jun 2026 14:30:15 +0200",
    body_html: str = "<p>Testinhalt</p>",
    include_to: bool = True,
) -> MIMEMultipart:
    """Erzeugt eine einfache HTML-E-Mail als MIMEMultipart-Objekt."""
    msg = MIMEMultipart("alternative")
    msg["From"] = from_
    if include_to:
        msg["To"] = to_
    msg["Subject"] = subject
    msg["Date"] = date_
    msg.attach(MIMEText(body_html, "html", "utf-8"))
    return msg


# ---------------------------------------------------------------------------
# Stufe 2: PDF-Inhalt
# ---------------------------------------------------------------------------

class TestPdfMetaHeader(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_2_1_alle_felder_vorhanden(self):
        """Von, An, Betreff und Gesendet müssen im PDF-Text stehen."""
        msg = make_simple_email(
            from_="Max Mustermann <max@example.com>",
            to_="john@example.com",
            subject="Testbetreff",
            date_="Thu, 11 Jun 2026 14:30:15 +0200",
        )
        pdf_path = self.out / "test_2_1.pdf"
        convert_and_save(msg, pdf_path)
        text = extract_pdf_text(pdf_path)

        self.assertRegex(text, r"Von:.+Max Mustermann",   "Von: fehlt oder falsch")
        self.assertRegex(text, r"An:.+john@example\.com", "An: fehlt oder falsch")
        self.assertRegex(text, r"Betreff:.+Testbetreff",  "Betreff: fehlt oder falsch")
        self.assertRegex(text, r"Gesendet:.+11\. Juni 2026", "Gesendet: fehlt oder falsches Datum")

    def test_2_2_kein_empfaenger_kein_absturz(self):
        """Fehlendes To:-Feld darf keinen Absturz verursachen; An: Zeile bleibt leer."""
        msg = make_simple_email(
            from_="sender@example.com",
            subject="Ohne Empfänger",
            date_="Fri, 12 Jun 2026 09:00:00 +0200",
            include_to=False,
        )
        pdf_path = self.out / "test_2_2.pdf"
        convert_and_save(msg, pdf_path)  # darf keine Exception werfen
        text = extract_pdf_text(pdf_path)

        # Von: muss vorhanden sein → E-Mail wird erkannt
        self.assertRegex(text, r"Von:.+sender@example\.com", "Von: fehlt")
        # An: Zeile im HTML erzeugt, auch wenn Inhalt leer
        self.assertIn("An:", text, "An:-Zeile fehlt komplett")

    def test_2_3_mime_kodierter_absender(self):
        """MIME-kodierter Absendername (Umlaute) muss im PDF dekodiert erscheinen."""
        # Erzeuge MIME-kodierten From-Header: "Günther Müller <g.mueller@example.com>"
        encoded_name = str(Header("Günther Müller", "utf-8"))
        msg = make_simple_email(
            from_=f"{encoded_name} <g.mueller@example.com>",
            to_="empf@example.com",
            subject="Umlaut-Test",
            date_="Mon, 15 Jun 2026 10:00:00 +0200",
        )
        pdf_path = self.out / "test_2_3.pdf"
        convert_and_save(msg, pdf_path)
        text = extract_pdf_text(pdf_path)

        # Keine rohen MIME-Escape-Sequenzen im PDF-Text
        self.assertNotIn("=?utf-8?", text, "MIME-Kodierung nicht aufgelöst")
        # Dekodierter Namensteil erkennbar (ü kann als 1 Zeichen oder 'ue' erscheinen)
        self.assertRegex(text, r"Von:.+M.{0,2}ller", "Dekodierter Name nicht gefunden")

    def test_2_4_mehrere_empfaenger(self):
        """Mehrere Empfänger in To: müssen vollständig im PDF erscheinen."""
        msg = make_simple_email(
            from_="sender@example.com",
            to_="alice@example.com, bob@example.com",
            subject="Multi-Empfänger",
            date_="Tue, 16 Jun 2026 11:00:00 +0200",
        )
        pdf_path = self.out / "test_2_4.pdf"
        convert_and_save(msg, pdf_path)
        text = extract_pdf_text(pdf_path)

        self.assertRegex(text, r"An:.+alice@example\.com", "Erster Empfänger fehlt")
        self.assertRegex(text, r"An:.+bob@example\.com",   "Zweiter Empfänger fehlt")

    def test_2_5_sonderzeichen_betreff(self):
        """Sonderzeichen (&, <, >) im Betreff müssen korrekt gerendert werden."""
        msg = make_simple_email(
            from_="sender@example.com",
            to_="empf@example.com",
            subject="Angebot & Vertrag <2026>",
            date_="Wed, 17 Jun 2026 12:00:00 +0200",
        )
        pdf_path = self.out / "test_2_5.pdf"
        convert_and_save(msg, pdf_path)
        text = extract_pdf_text(pdf_path)

        # Betreff erkennbar im PDF
        self.assertRegex(text, r"Betreff:.+Angebot", "Betreff-Text fehlt")
        # Keine HTML-Entities im extrahierten Text (xhtml2pdf hat sie aufgelöst)
        self.assertNotIn("&amp;", text, "Unaufgelöste HTML-Entity &amp; im PDF")
        self.assertNotIn("&lt;",  text, "Unaufgelöste HTML-Entity &lt; im PDF")


# ---------------------------------------------------------------------------
# Stufe 3: Kompatibilität mit correspondence_cleanup Regex-Mustern
# ---------------------------------------------------------------------------

class TestCleanupKompatibilitaet(unittest.TestCase):
    """
    Verifiziert, dass die Regex-Muster aus correspondence_cleanup_1_email.py
    auf die von email_archiver erzeugten PDFs matchen.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        msg = make_simple_email(
            from_="Hans Müller <hans@example.com>",
            to_="empf@company.com",
            subject="Besprechung Q3",
            date_="Thu, 11 Jun 2026 14:00:00 +0200",
        )
        pdf_path = self.out / "compat.pdf"
        convert_and_save(msg, pdf_path)
        self.text = extract_pdf_text(pdf_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_3_1_regex_von(self):
        m = re.search(r"Von: (.+)", self.text)
        self.assertIsNotNone(m, "Regex 'Von: (.+)' findet keinen Treffer")
        self.assertNotEqual(m.group(1).strip(), "", "Von: Inhalt ist leer")

    def test_3_2_regex_an(self):
        m = re.search(r"An: (.+)", self.text)
        self.assertIsNotNone(m, "Regex 'An: (.+)' findet keinen Treffer")
        self.assertNotEqual(m.group(1).strip(), "", "An: Inhalt ist leer")

    def test_3_3_regex_betreff(self):
        m = re.search(r"Betreff: (.+)", self.text)
        self.assertIsNotNone(m, "Regex 'Betreff: (.+)' findet keinen Treffer")
        self.assertIn("Besprechung", m.group(1), "Betreff-Inhalt falsch")

    def test_3_4_regex_gesendet(self):
        m = re.search(r"Gesendet:\s*(.+)", self.text)
        self.assertIsNotNone(m, "Regex 'Gesendet:\\s*(.+)' findet keinen Treffer")

    def test_3_5_deutsches_datumsformat(self):
        r"""Datumsformat '\d{1,2}. \w+ \d{4}' wie in _extract_email_date() erwartet."""
        m = re.search(r"\d{1,2}\. \w+ \d{4}", self.text)
        self.assertIsNotNone(m, "Deutsches Datumsformat nicht gefunden")
        self.assertEqual(m.group(), "11. Juni 2026", f"Datum falsch: '{m.group()}'")

    def test_3_6_email_wird_erkannt(self):
        """PDF darf nicht als 'not an email' klassifiziert werden."""
        sender_match    = re.search(r"Von: (.+)", self.text)
        recipient_match = re.search(r"An: (.+)", self.text)
        sender    = sender_match.group(1).strip()    if sender_match    else "N/A"
        recipient = recipient_match.group(1).strip() if recipient_match else "N/A"

        self.assertFalse(
            sender == "N/A" and recipient == "N/A",
            f"PDF wird nicht als E-Mail erkannt (Von='{sender}', An='{recipient}')",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
