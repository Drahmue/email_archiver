"""
Stufe-1-Tests: _format_date_german()

Ausführen:
    python tests/test_stage1_date_format.py
    oder: python -m pytest tests/test_stage1_date_format.py -v
"""

import sys
import unittest
from pathlib import Path

# src/ in den Suchpfad eintragen, damit converter importierbar ist
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from converter import _format_date_german


class TestFormatDateGerman(unittest.TestCase):

    def test_1_1_normaler_fall_sommer(self):
        """11. Juni 2026 — Standardfall, Sommerzeit (UTC+2)"""
        self.assertEqual(
            _format_date_german("Thu, 11 Jun 2026 14:30:15 +0200"),
            "11. Juni 2026",
        )

    def test_1_2_utc_mitternacht_naechster_tag(self):
        """UTC 23:00 → Berlin 00:00 Folgetag (Winterzeit UTC+1)"""
        self.assertEqual(
            _format_date_german("Thu, 1 Jan 2026 23:00:00 +0000"),
            "2. Januar 2026",
        )

    def test_1_3_jahresende(self):
        """31. Dezember — Jahreswechsel-Grenzfall"""
        self.assertEqual(
            _format_date_german("Wed, 31 Dec 2025 23:30:00 +0100"),
            "31. Dezember 2025",
        )

    def test_1_4_einstelliger_tag_umlaut(self):
        """5. März — einstelliger Tag und Umlaut im Monatsnamen"""
        self.assertEqual(
            _format_date_german("Wed, 5 Mar 2025 08:00:00 +0100"),
            "5. März 2025",
        )

    def test_1_5_alle_monate(self):
        """Alle 12 Monate werden korrekt auf deutschen Namen gemappt."""
        cases = [
            ("Tue, 1 Jan 2026 12:00:00 +0100",  "Januar"),
            ("Sun, 1 Feb 2026 12:00:00 +0100",  "Februar"),
            ("Sun, 1 Mar 2026 12:00:00 +0100",  "März"),
            ("Wed, 1 Apr 2026 12:00:00 +0200",  "April"),
            ("Fri, 1 May 2026 12:00:00 +0200",  "Mai"),
            ("Mon, 1 Jun 2026 12:00:00 +0200",  "Juni"),
            ("Wed, 1 Jul 2026 12:00:00 +0200",  "Juli"),
            ("Sat, 1 Aug 2026 12:00:00 +0200",  "August"),
            ("Tue, 1 Sep 2026 12:00:00 +0200",  "September"),
            ("Thu, 1 Oct 2026 12:00:00 +0200",  "Oktober"),
            ("Sun, 1 Nov 2026 12:00:00 +0100",  "November"),
            ("Tue, 1 Dec 2026 12:00:00 +0100",  "Dezember"),
        ]
        for date_str, expected_month in cases:
            with self.subTest(monat=expected_month):
                result = _format_date_german(date_str)
                self.assertIn(expected_month, result, f"Monat '{expected_month}' nicht in '{result}'")

    def test_1_6_leerer_string_fallback(self):
        """Leerer String: unverändert zurückgeben, kein Absturz."""
        self.assertEqual(_format_date_german(""), "")

    def test_1_7_ungültiges_format_fallback(self):
        """Nicht-parsebares Datum: Eingabe unverändert zurückgeben."""
        self.assertEqual(_format_date_german("kein datum"), "kein datum")


if __name__ == "__main__":
    unittest.main(verbosity=2)
