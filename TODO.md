# TODO — email_archiver

---

## Offen

---

## Erledigt

### Setup & Konfiguration
- [x] **`README.md` ausgebaut** (2026-07-10) — Projektbeschreibung, Installation, Konfiguration, correspondence_cleanup-Kompatibilität
- [x] **`beautifulsoup4`** zu `requirements.txt` hinzugefügt (2026-07-10)
- [x] **Projektstruktur initialisiert** (2026-06-12, Commit `ff5b1eb`)
- [x] **`requirements.txt` korrigiert** (2026-06-12) — weasyprint, pikepdf, imapclient, ahlib
- [x] **`config/config.ini.template` korrigiert** (2026-06-12) — vollständige [imap]/[output]/[logging]-Struktur
- [x] **SPECIFICATION.md** ausgearbeitet — vollständige Anforderungen, Architektur, Implementierungshinweise
- [x] **CHANGELOG.md, TODO.md, CLAUDE.md** angelegt (2026-06-12)

### Implementierung
- [x] **`src/utils.py`** implementiert (2026-06-12)
- [x] **`src/imap_client.py`** implementiert (2026-06-12)
- [x] **`src/converter.py`** implementiert (2026-06-12)
- [x] **`src/main.py`** implementiert (2026-06-12)
- [x] **Ordnerstruktur** angelegt: `src/`, `tests/`, `logs/`, `data/` (2026-06-12)

### HTML-Vorverarbeitung & PDF-Qualität
- [x] **HTML-Engine gewechselt**: weasyprint → xhtml2pdf für Umlaut-Support (2026-07)
- [x] **Arial-Font-Registrierung** via reportlab TTF (2026-07)
- [x] **`_strip_mso_css()`** — entfernt `@list`-CSS-At-Regeln die xhtml2pdf nicht parsen kann (2026-07)
- [x] **`_resolve_cid_images()`** — Inline-Bilder (cid:-Referenzen) als data:-URIs einbetten (2026-07)
- [x] **`_normalize_tables()`** — Outlook-Tabellen normalisieren:
  - schwarze Rahmen → graue Rahmen für Datentabellen (2026-07)
  - Layout-Tabellen (border:none im CSS) ohne Rahmen und ohne erzwungene Breite (2026-07)
  - `width` aus HTML-Attributen und style-Strings entfernen (2026-07)
  - Outlook-Muster `border="1"` + `style="border:none"` = Layout-Tabelle (2026-07-10)
- [x] **Inline-Bilder**: Content-ID-Parts nicht als Dateianhang einbetten (2026-07)

### correspondence_cleanup-Kompatibilität
- [x] **Deutsches Datumsformat** (`_format_date_german()`) für Gesendet-Feld (2026-07)
- [x] **Label `Gesendet:` statt `Datum:`** — passend zu correspondence_cleanup Regex (2026-07)
- [x] **`An:`-Feld** im Metadaten-Header ergänzt (2026-07)

### Tests
- [x] **`tests/test_stage1_date_format.py`** — 7 Tests für `_format_date_german()` (2026-07)
- [x] **`tests/test_stage2_pdf_content.py`** — 11 Tests: PDF-Inhalt + Regex-Kompatibilität (2026-07)
- [x] **`tests/test_stage3_endtoend.py`** — 5 Tests: correspondence_cleanup End-to-End (2026-07)
- [x] **`tests/test_stage4_regression.py`** — 26 Tests: CID-Bilder, URL-Blocking, Anhänge, Dateinamen (2026-07)
