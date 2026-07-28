# Changelog — email_archiver

Alle wesentlichen Änderungen am Projekt werden hier dokumentiert.
Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

---

## [Unreleased]

### Geändert
- **Fix: Externe Bilder im PDF** (`converter.py`) — neue Funktion `_resolve_external_images()` lädt `<img src="https://...">`-Bilder via urllib vor dem Playwright-Rendering herunter und bettet sie als `data:`-URIs ein; Playwright blockiert weiterhin alle externen Requests (Tracking-Schutz bleibt erhalten)

---

## [0.4.0] - 2026-07-13

### Hinzugefügt
- **`run_archiver.ps1`** — PowerShell-Startskript: aktiviert `.venv` und ruft `src/main.py` auf
- **Thread-Deduplizierung** (`main.py`) — E-Mails, deren `Message-ID` im `References`- oder `In-Reply-To`-Header einer neueren E-Mail im selben Batch auftaucht, werden übersprungen (kein PDF) aber trotzdem nach `processed_folder` verschoben; verhindert redundante PDFs wenn Thunderbird einen ganzen Thread verschiebt

### Geändert
- **HTML-Engine gewechselt**: `xhtml2pdf` → **Playwright (Headless Chromium)**
  - Volle CSS-Unterstützung; Tabellen umbrechen korrekt über mehrere Seiten
  - Externe URLs via `page.route()` auf Netzwerkebene blockiert (statt xhtml2pdf `link_callback`)
  - Browser-Singleton mit `atexit`-Cleanup (`_get_browser()` / `_shutdown_browser()`)
  - Preprocessing-Pipeline entfernt (`_strip_mso_css`, `_normalize_tables`, `_unwrap_single_cell_tables` nicht mehr nötig)
- **Fix: Outlook WordSection-Seitenumbruch** — Outlook-HTML definiert benannte CSS-Seiten (`page: WordSection1`), die Chromium im Druckmodus als Seitenumbruch interpretiert; wird durch `page: auto !important` in injiziertem Print-CSS neutralisiert
- **`requirements.txt`** — `xhtml2pdf` und `beautifulsoup4` entfernt, `playwright` hinzugefügt
- **Tests** — `_block_external_urls`-Unit-Tests entfernt (URL-Blocking jetzt auf Playwright-Ebene); `ff`-Ligatur-Toleranz in PDF-Textextraktion ergänzt (`\s*` im Regex); 44 Tests, alle grün

---

## [0.3.0] - 2026-07-10

### Hinzugefügt
- **`beautifulsoup4`** zu `requirements.txt` — Abhängigkeit für `_normalize_tables()`
- **4-stufige Testsuite** (`tests/`) mit 44 Tests:
  - `test_stage1_date_format.py` — Unit-Tests für `_format_date_german()` (7 Tests)
  - `test_stage2_pdf_content.py` — PDF-Inhalt und correspondence_cleanup-Kompatibilität (11 Tests)
  - `test_stage3_endtoend.py` — End-to-End-Test mit `process_pdf_file()` aus correspondence_cleanup (5 Tests)
  - `test_stage4_regression.py` — Regressionstests: CID-Bilder, URL-Blocking, Anhänge, Dateinamen (21 Tests)

### Geändert
- **HTML-Engine gewechselt**: `weasyprint` → `xhtml2pdf` (pisa) für zuverlässigeres Umlaut-Rendering
- **Font-Registrierung**: Arial TTF aus `C:\Windows\Fonts` via `reportlab.pdfbase` für vollständigen Unicode-Support
- **HTML-Preprocessing-Pipeline**:
  - `_strip_mso_css()` — entfernt `@list`-CSS-At-Regeln (MSO-proprietär, bricht xhtml2pdf)
  - `_normalize_tables()` — normalisiert Outlook-Tabellen (Datentabellen vs. Layout-Tabellen)
  - `_resolve_cid_images()` — ersetzt `cid:`-Referenzen durch base64-`data:`-URIs
- **Metadaten-Header**: Von / An / Betreff / Gesendet als sichtbarer Block oben im PDF
- **Anhänge**: Inline-Bilder mit `Content-ID`-Header werden übersprungen

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
