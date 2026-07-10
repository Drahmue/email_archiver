"""
Stufe-4-Regressionstests: bestehende Funktionen nach Metadaten-Änderung

Testet:
  4.1  _resolve_cid_images()  — cid:-Bilder werden als data:-URI eingebettet
  4.2  _block_external_urls() — externe URLs werden blockiert, lokale nicht
  4.3  Anhänge via pikepdf eingebettet und lesbar
  4.4  build_pdf_filename()   — Namensformat, Absender-Auswahl, Kollision

Ausführen:
    python tests/test_stage4_regression.py
    oder: python -m pytest tests/test_stage4_regression.py -v
"""

import base64
import os
import sys
import tempfile
import unittest
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pikepdf

_project_root = Path(__file__).parent.parent
os.chdir(_project_root)
sys.path.insert(0, str(_project_root / "src"))

from converter import _block_external_urls, _resolve_cid_images, convert_and_save
from utils import build_pdf_filename

# Valides 1×1-Pixel-PNG (grau) — von PIL/xhtml2pdf dekodierbar
_MINIMAL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAAAAAA6fptVAAAACklEQVQI12NgAAAAAgAB4iG8MwAAAABJRU5ErkJggg=="
)


# ---------------------------------------------------------------------------
# 4.1 — CID-Inline-Bilder
# ---------------------------------------------------------------------------

class TestCidImages(unittest.TestCase):
    """_resolve_cid_images() ersetzt cid:-Referenzen durch data:-URIs."""

    def _make_related_msg(self, cid: str, img_data: bytes) -> MIMEMultipart:
        msg = MIMEMultipart("related")
        img_part = MIMEImage(img_data, "png")
        img_part.add_header("Content-ID", f"<{cid}>")
        msg.attach(img_part)
        return msg

    def test_4_1_cid_wird_zu_data_uri(self):
        """cid:-Referenz muss durch data:image/png;base64,... ersetzt werden."""
        cid = "test-image@example.com"
        msg = self._make_related_msg(cid, _MINIMAL_PNG)
        html = f'<img src="cid:{cid}">'

        result = _resolve_cid_images(msg, html)

        self.assertNotIn("cid:", result, "cid: nicht ersetzt")
        self.assertIn("data:image/png;base64,", result, "data:-URI fehlt")

    def test_4_1_base64_inhalt_korrekt(self):
        """Eingebettetes base64 muss den originalen Bilddaten entsprechen."""
        cid = "img001@test.com"
        msg = self._make_related_msg(cid, _MINIMAL_PNG)
        html = f'<img src="cid:{cid}">'

        result = _resolve_cid_images(msg, html)

        # data:-URI extrahieren und dekodieren
        prefix = "data:image/png;base64,"
        start = result.index(prefix) + len(prefix)
        # base64 endet bei " oder '
        end = result.index('"', start) if '"' in result[start:] else len(result)
        decoded = base64.b64decode(result[start:end])
        self.assertEqual(decoded, _MINIMAL_PNG, "Bilddaten nach base64-Roundtrip verändert")

    def test_4_1_mehrere_cid_bilder(self):
        """Mehrere cid:-Referenzen im selben HTML werden alle aufgelöst."""
        msg = MIMEMultipart("related")
        for i, cid in enumerate(["img1@test", "img2@test"]):
            part = MIMEImage(_MINIMAL_PNG, "png")
            part.add_header("Content-ID", f"<{cid}>")
            msg.attach(part)

        html = '<img src="cid:img1@test"><img src="cid:img2@test">'
        result = _resolve_cid_images(msg, html)

        self.assertNotIn("cid:", result, "Nicht alle cid:-Referenzen ersetzt")
        self.assertEqual(result.count("data:image/png;base64,"), 2,
                          "Nicht alle Bilder eingebettet")

    def test_4_1_keine_cid_in_html_bleibt_unveraendert(self):
        """HTML ohne cid:-Referenzen darf nicht verändert werden."""
        msg = MIMEMultipart("related")
        html = "<p>Kein Bild hier</p>"
        result = _resolve_cid_images(msg, html)
        self.assertEqual(result, html)

    def test_4_1_unbekannte_cid_bleibt_unveraendert(self):
        """Unbekannte cid:-Referenz (kein passender Part) bleibt unverändert."""
        msg = MIMEMultipart("related")  # keine Bild-Parts
        html = '<img src="cid:ghost@unknown">'
        result = _resolve_cid_images(msg, html)
        self.assertIn("cid:ghost@unknown", result, "Unbekannte cid: wurde entfernt")


# ---------------------------------------------------------------------------
# 4.2 — URL-Blockierung
# ---------------------------------------------------------------------------

class TestUrlBlocking(unittest.TestCase):
    """_block_external_urls() blockiert HTTP/HTTPS, erlaubt lokale Pfade."""

    def test_4_2_https_blockiert(self):
        result = _block_external_urls("https://tracker.example.com/pixel.gif", "")
        self.assertIsNone(result, "HTTPS-URL nicht blockiert")

    def test_4_2_http_blockiert(self):
        result = _block_external_urls("http://example.com/image.png", "")
        self.assertIsNone(result, "HTTP-URL nicht blockiert")

    def test_4_2_protocol_relative_blockiert(self):
        result = _block_external_urls("//cdn.example.com/style.css", "")
        self.assertIsNone(result, "Protokoll-relative URL nicht blockiert")

    def test_4_2_lokaler_pfad_erlaubt(self):
        result = _block_external_urls("/local/path/image.png", "")
        self.assertIsNotNone(result, "Lokaler Pfad fälschlicherweise blockiert")

    def test_4_2_data_uri_erlaubt(self):
        data_uri = "data:image/png;base64,iVBORw0KGgo="
        result = _block_external_urls(data_uri, "")
        self.assertIsNotNone(result, "data:-URI fälschlicherweise blockiert")

    def test_4_2_email_mit_externer_url_kein_absturz(self):
        """E-Mail mit externem Tracking-Pixel darf keinen Absturz verursachen."""
        tmp = tempfile.TemporaryDirectory()
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = "sender@example.com"
            msg["To"] = "empf@example.com"
            msg["Subject"] = "Tracking-Test"
            msg["Date"] = "Thu, 11 Jun 2026 14:00:00 +0200"
            html = (
                '<html><body>'
                '<p>Text</p>'
                '<img src="https://tracker.example.com/open?id=123" width="1" height="1">'
                '</body></html>'
            )
            msg.attach(MIMEText(html, "html", "utf-8"))
            pdf_path = Path(tmp.name) / "tracking.pdf"
            convert_and_save(msg, pdf_path)  # darf nicht werfen
            self.assertTrue(pdf_path.exists(), "PDF nicht erzeugt")
            self.assertGreater(pdf_path.stat().st_size, 0, "PDF ist leer")
        finally:
            tmp.cleanup()


# ---------------------------------------------------------------------------
# 4.3 — Anhänge via pikepdf eingebettet
# ---------------------------------------------------------------------------

class TestAttachments(unittest.TestCase):
    """Dateianhänge müssen als EmbeddedFile im PDF erscheinen."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_email_with_attachment(
        self, filename: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> MIMEMultipart:
        msg = MIMEMultipart("mixed")
        msg["From"] = "sender@example.com"
        msg["To"] = "empf@example.com"
        msg["Subject"] = "Mit Anhang"
        msg["Date"] = "Thu, 11 Jun 2026 14:00:00 +0200"
        msg.attach(MIMEText("<p>E-Mail mit Anhang</p>", "html", "utf-8"))
        att = MIMEApplication(data)
        att.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(att)
        return msg

    def test_4_3_anhang_eingebettet(self):
        """Einfacher Textanhang muss im PDF-Attachment-Panel erscheinen."""
        msg = self._make_email_with_attachment("beilage.txt", b"Inhalt der Beilage")
        pdf_path = self.out / "test_4_3.pdf"
        convert_and_save(msg, pdf_path)

        with pikepdf.open(pdf_path) as pdf:
            self.assertIn("beilage.txt", pdf.attachments,
                          "Anhang 'beilage.txt' nicht im PDF eingebettet")

    def test_4_3_anhang_inhalt_korrekt(self):
        """Eingebetteter Anhang muss die originalen Bytes enthalten."""
        original_data = b"Originaldaten fuer Integritaetstest 12345"
        msg = self._make_email_with_attachment("check.txt", original_data)
        pdf_path = self.out / "test_4_3_inhalt.pdf"
        convert_and_save(msg, pdf_path)

        with pikepdf.open(pdf_path) as pdf:
            self.assertIn("check.txt", pdf.attachments)
            embedded = pdf.attachments["check.txt"].get_file().read_bytes()
            self.assertEqual(embedded, original_data,
                              "Anhang-Inhalt nach Einbettung verändert")

    def test_4_3_mehrere_anhaenge(self):
        """Mehrere Anhänge müssen alle eingebettet werden."""
        msg = MIMEMultipart("mixed")
        msg["From"] = "sender@example.com"
        msg["To"] = "empf@example.com"
        msg["Subject"] = "Zwei Anhänge"
        msg["Date"] = "Thu, 11 Jun 2026 14:00:00 +0200"
        msg.attach(MIMEText("<p>Zwei Anhänge</p>", "html", "utf-8"))

        for name, data in [("eins.txt", b"Datei 1"), ("zwei.txt", b"Datei 2")]:
            att = MIMEApplication(data)
            att.add_header("Content-Disposition", "attachment", filename=name)
            msg.attach(att)

        pdf_path = self.out / "test_4_3_multi.pdf"
        convert_and_save(msg, pdf_path)

        with pikepdf.open(pdf_path) as pdf:
            self.assertIn("eins.txt", pdf.attachments, "'eins.txt' fehlt")
            self.assertIn("zwei.txt", pdf.attachments, "'zwei.txt' fehlt")

    def test_4_3_keine_anhaenge_kein_fehler(self):
        """E-Mail ohne Anhänge darf keinen Fehler verursachen."""
        msg = MIMEMultipart("alternative")
        msg["From"] = "sender@example.com"
        msg["To"] = "empf@example.com"
        msg["Subject"] = "Ohne Anhang"
        msg["Date"] = "Thu, 11 Jun 2026 14:00:00 +0200"
        msg.attach(MIMEText("<p>Kein Anhang</p>", "html", "utf-8"))

        pdf_path = self.out / "test_4_3_leer.pdf"
        convert_and_save(msg, pdf_path)  # darf nicht werfen
        self.assertTrue(pdf_path.exists())

        with pikepdf.open(pdf_path) as pdf:
            self.assertEqual(len(pdf.attachments), 0,
                              "Leere E-Mail hat unerwartete Attachments")

    def test_4_3_inline_bild_nicht_als_anhang(self):
        """Inline-Bilder (Content-ID) dürfen nicht als PDF-Anhang erscheinen."""
        msg = MIMEMultipart("related")
        msg["From"] = "sender@example.com"
        msg["To"] = "empf@example.com"
        msg["Subject"] = "Mit Inline-Bild"
        msg["Date"] = "Thu, 11 Jun 2026 14:00:00 +0200"
        msg.attach(MIMEText('<p><img src="cid:logo@example.com"></p>', "html", "utf-8"))

        # Inline-Bild mit Content-ID (z.B. Logo in E-Mail-Signatur)
        img_part = MIMEImage(_MINIMAL_PNG, "png")
        img_part.add_header("Content-ID", "<logo@example.com>")
        img_part.add_header("Content-Disposition", "inline", filename="logo.png")
        msg.attach(img_part)

        pdf_path = self.out / "test_4_3_inline.pdf"
        convert_and_save(msg, pdf_path)

        with pikepdf.open(pdf_path) as pdf:
            self.assertEqual(len(pdf.attachments), 0,
                              "Inline-Bild fälschlicherweise als PDF-Anhang eingebettet")

    def test_4_3_inline_bild_und_echter_anhang(self):
        """Inline-Bild wird nicht eingebettet, echter Anhang schon."""
        msg = MIMEMultipart("mixed")
        msg["From"] = "sender@example.com"
        msg["To"] = "empf@example.com"
        msg["Subject"] = "Bild + Anhang"
        msg["Date"] = "Thu, 11 Jun 2026 14:00:00 +0200"

        related = MIMEMultipart("related")
        related.attach(MIMEText('<p><img src="cid:logo@example.com"></p>', "html", "utf-8"))
        img_part = MIMEImage(_MINIMAL_PNG, "png")
        img_part.add_header("Content-ID", "<logo@example.com>")
        img_part.add_header("Content-Disposition", "inline", filename="logo.png")
        related.attach(img_part)
        msg.attach(related)

        att = MIMEApplication(b"Echter Anhang")
        att.add_header("Content-Disposition", "attachment", filename="dokument.pdf")
        msg.attach(att)

        pdf_path = self.out / "test_4_3_mixed.pdf"
        convert_and_save(msg, pdf_path)

        with pikepdf.open(pdf_path) as pdf:
            self.assertNotIn("logo.png", pdf.attachments,
                              "Inline-Bild fälschlicherweise als Anhang eingebettet")
            self.assertIn("dokument.pdf", pdf.attachments,
                          "Echter Anhang fehlt im PDF")


# ---------------------------------------------------------------------------
# 4.4 — Dateinamenskonvention (build_pdf_filename)
# ---------------------------------------------------------------------------

class TestFilenameConvention(unittest.TestCase):
    """build_pdf_filename() erzeugt korrekte Dateinamen nach Konvention."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.date_str = "Thu, 11 Jun 2026 14:30:15 +0200"

    def tearDown(self):
        self.tmp.cleanup()

    def test_4_4_grundformat(self):
        """Dateiname muss dem Schema YYYY-MM-DD_HH-MM_Absender.pdf folgen."""
        path = build_pdf_filename(self.date_str, "sender@example.com", self.out)
        self.assertRegex(
            path.name,
            r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}_.+\.pdf$",
            f"Dateiname entspricht nicht dem Schema: '{path.name}'",
        )

    def test_4_4_datum_korrekt(self):
        """Datum im Dateinamen muss dem Date-Header entsprechen (Berlin-Zeit)."""
        path = build_pdf_filename(self.date_str, "sender@example.com", self.out)
        self.assertTrue(
            path.name.startswith("2026-06-11_14-30_"),
            f"Datum/Uhrzeit falsch: '{path.name}'",
        )

    def test_4_4_display_name_bevorzugt(self):
        """Display Name wird gegenüber E-Mail-Adresse bevorzugt."""
        path = build_pdf_filename(
            self.date_str, "Max Mustermann <max@example.com>", self.out
        )
        self.assertIn("Max_Mustermann", path.name,
                       f"Display Name nicht im Dateinamen: '{path.name}'")
        self.assertNotIn("max@example", path.name,
                          f"E-Mail-Adresse statt Display Name verwendet: '{path.name}'")

    def test_4_4_email_adresse_als_fallback(self):
        """Ohne Display Name wird die E-Mail-Adresse verwendet."""
        path = build_pdf_filename(self.date_str, "noreply@example.com", self.out)
        self.assertIn("noreply", path.name,
                       f"E-Mail-Adresse nicht im Dateinamen: '{path.name}'")

    def test_4_4_sonderzeichen_werden_ersetzt(self):
        """Sonderzeichen im Absender werden durch Unterstriche ersetzt."""
        path = build_pdf_filename(
            self.date_str, "Müller & Söhne <ms@example.com>", self.out
        )
        # Kein &, keine Leerzeichen im Dateinamen
        self.assertNotIn("&", path.name)
        self.assertNotIn(" ", path.name)
        self.assertTrue(path.suffix == ".pdf")

    def test_4_4_kollision_suffix_2(self):
        """Bei vorhandenem Dateinamen wird _2 als Suffix angehängt."""
        # Ersten Dateinamen erzeugen und die Datei anlegen
        path1 = build_pdf_filename(self.date_str, "sender@example.com", self.out)
        path1.touch()

        path2 = build_pdf_filename(self.date_str, "sender@example.com", self.out)
        self.assertNotEqual(path1, path2, "Kollision nicht aufgelöst")
        self.assertIn("_2", path2.stem, f"Suffix '_2' fehlt: '{path2.name}'")

    def test_4_4_kollision_suffix_3(self):
        """Bei zwei vorhandenen Dateien wird _3 verwendet."""
        path1 = build_pdf_filename(self.date_str, "sender@example.com", self.out)
        path1.touch()
        path2 = build_pdf_filename(self.date_str, "sender@example.com", self.out)
        path2.touch()

        path3 = build_pdf_filename(self.date_str, "sender@example.com", self.out)
        self.assertIn("_3", path3.stem, f"Suffix '_3' fehlt: '{path3.name}'")

    def test_4_4_ungültiges_datum_wirft_fehler(self):
        """Nicht-parsebares Datum muss ValueError auslösen."""
        with self.assertRaises(ValueError):
            build_pdf_filename("kein datum", "sender@example.com", self.out)

    def test_4_4_berlin_zeitzone(self):
        """UTC-Datum muss in Berliner Ortszeit umgerechnet werden."""
        # UTC 23:30 → Berlin 00:30 Folgetag (Winterzeit)
        path = build_pdf_filename(
            "Thu, 1 Jan 2026 23:30:00 +0000", "sender@example.com", self.out
        )
        self.assertTrue(
            path.name.startswith("2026-01-02_00-30_"),
            f"Zeitzone nicht nach Berlin konvertiert: '{path.name}'",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
