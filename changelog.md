# Changelog — email_archiver

Alle wesentlichen Änderungen am Projekt werden hier dokumentiert.
Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

---

## [Unreleased]

### Hinzugefügt
- **`beautifulsoup4`** zu `requirements.txt` — Abhängigkeit für `_normalize_tables()`
- **4-stufige Testsuite** (`tests/`) mit 49 Tests:
  - `test_stage1_date_format.py` — Unit-Tests für `_format_date_german()` (7 Tests)
  - `test_stage2_pdf_content.py` — PDF-Inhalt und correspondence_cleanup-Kompatibilität (11 Tests)
  - `test_stage3_endtoend.py` — End-to-End-Test mit `process_pdf_file()` aus correspondence_cleanup (5 Tests)
  - `test_stage4_regression.py` — Regressionstests: CID-Bilder, URL-Blocking, Anhänge, Dateinamen (26 Tests)

### Geändert (converter.py — gegenüber initialer Implementierung)

- **HTML-Engine gewechselt**: `weasyprint` → `xhtml2pdf` (pisa) für zuverlässigeres Umlaut-Rendering
- **Font-Registrierung**: Arial TTF aus `C:\Windows\Fonts` via `reportlab.pdfbase` für vollständigen Unicode-Support
- **HTML-Preprocessing-Pipeline** (vor der PDF-Erzeugung):
  - `_strip_mso_css()` — entfernt `@list`-CSS-At-Regeln (MSO-proprietär, bricht xhtml2pdf)
  - `_normalize_tables()` — normalisiert Outlook-Tabellen: unterscheidet Datentabellen (border > 0, graue Rahmen, volle Breite) von Layout-Tabellen (border:none im CSS, keine Rahmen, keine Breitenänderung); entfernt `width` aus HTML-Attributen und style-Strings; erkennt Outlook-Muster `border="1"` + `style="border:none"` korrekt als Layout-Tabelle
  - `_resolve_cid_images()` — ersetzt `cid:`-Referenzen durch base64-`data:`-URIs (Inline-Bilder in multipart/related)
- **Metadaten-Header**: Von / An / Betreff / Gesendet als sichtbarer Block oben im PDF
  - Datum in deutschem Langformat: `_format_date_german()` (z. B. "3. Juli 2026")
  - Label `Gesendet:` statt `Datum:` (Kompatibilität mit correspondence_cleanup)
  - `An:`-Feld ergänzt (correspondence_cleanup extrahiert Empfänger)
- **Anhänge**: Inline-Bilder mit `Content-ID`-Header werden übersprungen — sie sind bereits im PDF-Body gerendert und sollen nicht als Dateianhang eingebettet werden

---

## [0.2.0] - 2026-06-12

### Hinzugefügt
- **`src/utils.py`** — Hilfsfunktionen: `decode_mime_header()`, `sanitize_filename()`, `build_pdf_filename()` mit Kollisionsauflösung und Europe/Berlin-Zeitzone
- **`src/imap_client.py`** — IMAP-Operationen via imapclient: `connect()`, `fetch_emails()`, `move_email()` (MOVE mit Fallback auf COPY+DELETE), `disconnect()`
- **`src/converter.py`** — E-Mail-zu-PDF-Konvertierung: Body-Extraktion (HTML/Plain-Text), Metadaten-Header-Block, xhtml2pdf-Rendering mit URL-Blocking, pikepdf-Anhang-Einbettung
- **`src/main.py`** — Einstiegspunkt: Konfiguration laden, Logging via ahlib, IMAP verbinden, pro E-Mail konvertieren + verschieben, Fehlerbehandlung, Abschluss-Zusammenfassung
- Ordnerstruktur `src/`, `tests/`, `logs/`, `data/` angelegt

### Geändert
- `SPECIFICATION.md` überarbeitet — Details zu Dateinamenskonvention, Bibliotheksauswahl, Verarbeitungsablauf und Implementierungshinweisen ergänzt
- `requirements.txt` korrigiert — falschen Standard-Template-Inhalt ersetzt durch projektspezifische Abhängigkeiten
- `config/config.ini.template` korrigiert — generischen Platzhalter ersetzt durch vollständige [imap]/[output]/[logging]-Struktur

---

## [0.1.0] - 2026-06-12

### Hinzugefügt
- **Projektstruktur initialisiert** (Commit `ff5b1eb`)
  - `SPECIFICATION.md`, `README.md`, `requirements.txt`, `config/config.ini.template`
  - `.gitignore`, `Python_Standard_Prompt.md`, `.venv/`

### Begründung
Projekt ersetzt das Outlook-Add-in "Sperry Software Save as PDF" durch eine vollautomatische IMAP-basierte Lösung.
