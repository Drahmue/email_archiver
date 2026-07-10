"""
Stufe-3-Tests: End-to-End-Kompatibilität mit correspondence_cleanup_1_email.py

Erzeugt ein echtes PDF via email_archiver und ruft process_pdf_file() aus
correspondence_cleanup_1_email.py direkt darauf auf. Prüft:
- rename == True  (PDF wird als E-Mail erkannt)
- Datum im Zieldateinamen ist kein "N/A"  (Gesendet-Feld korrekt geparst)

Voraussetzung: correspondence_cleanup muss unter dem konfigurierten Pfad liegen.

Ausführen:
    python tests/test_stage3_endtoend.py
    oder: python -m pytest tests/test_stage3_endtoend.py -v
"""

import configparser
import os
import sys
import tempfile
import unittest
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# Projektwurzel als Arbeitsverzeichnis
_project_root = Path(__file__).parent.parent
os.chdir(_project_root)
sys.path.insert(0, str(_project_root / "src"))

from converter import convert_and_save

_CC_DIR = Path(r"C:\Users\ah\Dev\correspondence_cleanup")
_CC_AVAILABLE = (
    _CC_DIR.is_dir()
    and (_CC_DIR / "correspondence_cleanup_1_email.py").exists()
)


def _build_analyzer(tmp_dir: str):
    """
    Erzeugt einen EmailAnalyzer mit minimaler In-Memory-Konfiguration.
    Die Listen-Dateien müssen nicht existieren — _load_2column_list()
    gibt bei FileNotFoundError ein leeres Dict zurück.
    """
    if str(_CC_DIR) not in sys.path:
        sys.path.insert(0, str(_CC_DIR))
    from correspondence_cleanup_1_email import EmailAnalyzer

    config = configparser.ConfigParser()
    config["Paths"] = {
        "system_folder": tmp_dir,
        "target_folder": tmp_dir,
    }
    config["Settings"] = {
        "unknown_folder": "unbekannt",
        "user_id": "ah",
    }
    config["Files"] = {
        "log_file": "test_stage3.log",
        "cleanup_list": "nonexistent_cleanup.txt",
        "replacement_list": "nonexistent_replacements.txt",
        "typo_list": "nonexistent_typos.txt",
        "known_list": "nonexistent_known.txt",
    }
    return EmailAnalyzer(config)


@unittest.skipUnless(
    _CC_AVAILABLE,
    f"Übersprungen: correspondence_cleanup nicht gefunden unter {_CC_DIR}",
)
class TestEndToEnd(unittest.TestCase):
    """
    Ruft process_pdf_file() aus correspondence_cleanup_1_email.py direkt
    auf ein von email_archiver erzeugtes PDF auf.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

        # Standard-Test-E-Mail erzeugen und als PDF speichern
        msg = MIMEMultipart("alternative")
        msg["From"] = "sender@example.com"
        msg["To"] = "empf@example.com"
        msg["Subject"] = "Besprechung Q3"
        msg["Date"] = "Thu, 11 Jun 2026 14:00:00 +0200"
        msg.attach(MIMEText("<p>Testinhalt</p>", "html", "utf-8"))

        self.pdf_path = self.out / "test_email.pdf"
        convert_and_save(msg, self.pdf_path)

        self.analyzer = _build_analyzer(str(self.out))

    def tearDown(self):
        self.tmp.cleanup()

    def test_3_7_rename_ist_true(self):
        """PDF mit Von: und An: muss als E-Mail erkannt werden (rename=True)."""
        results, rename = self.analyzer.process_pdf_file(str(self.pdf_path))
        self.assertTrue(rename, "PDF nicht als E-Mail erkannt — rename=False")

    def test_3_7_datum_nicht_na(self):
        """Datum im Zieldateinamen muss im Format YYYYMMDD vorliegen, nicht 'N/A'."""
        results, rename = self.analyzer.process_pdf_file(str(self.pdf_path))
        self.assertTrue(results, "process_pdf_file() lieferte leere Ergebnisliste")
        target_name = results[0][0]
        self.assertNotIn(
            "N/A", target_name,
            f"Datum nicht extrahiert — Zieldateiname: '{target_name}'",
        )
        self.assertRegex(
            target_name, r"\d{8}",
            f"Kein YYYYMMDD-Datum in Zieldateiname: '{target_name}'",
        )

    def test_3_7_absender_im_dateinamen(self):
        """Absender-Domain muss im Zieldateinamen erkennbar sein."""
        results, rename = self.analyzer.process_pdf_file(str(self.pdf_path))
        self.assertTrue(results)
        target_name = results[0][0]
        self.assertIn(
            "example", target_name.lower(),
            f"Absender nicht im Zieldateinamen: '{target_name}'",
        )

    def test_3_7_betreff_im_dateinamen(self):
        """Betreff muss (bereinigt) im Zieldateinamen erscheinen."""
        results, rename = self.analyzer.process_pdf_file(str(self.pdf_path))
        self.assertTrue(results)
        target_name = results[0][0]
        self.assertIn(
            "Besprechung", target_name,
            f"Betreff nicht im Zieldateinamen: '{target_name}'",
        )

    def test_3_7_display_name_mit_umlauten(self):
        """E-Mail mit Absender-Displayname mit Umlaut wird korrekt verarbeitet."""
        msg = MIMEMultipart("alternative")
        msg["From"] = "Günther Müller <g.mueller@example.com>"
        msg["To"] = "empf@example.com"
        msg["Subject"] = "Umlaut-Test"
        msg["Date"] = "Fri, 12 Jun 2026 10:00:00 +0200"
        msg.attach(MIMEText("<p>Test</p>", "html", "utf-8"))

        pdf_path = self.out / "umlaut_test.pdf"
        convert_and_save(msg, pdf_path)

        results, rename = self.analyzer.process_pdf_file(str(pdf_path))
        self.assertTrue(rename, "PDF mit Umlaut-Absender nicht erkannt")
        self.assertTrue(results)
        target_name = results[0][0]
        self.assertNotIn("N/A", target_name,
                          f"Fehlerhafter Zieldateiname: '{target_name}'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
