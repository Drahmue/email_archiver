# TODO — email_archiver

---

## Offen

- [ ] **Leere letzte Seite** im PDF untersuchen (z.B. Revolut-Mail: Seite 3 leer) — offen, 2026-10-18
- [ ] **Übrige PDFs aus Testlauf 2026-10-18 prüfen** (`2026-10-15_*_Dr_Alexander_Haunschild.pdf`), ggf. bei Bedarf neu erzeugen — offen, 2026-10-18
- [ ] **Ältere Archiv-PDFs auf fehlenden Fließtext prüfen** (Webfont-Timing-Bug vor `f163b88`, betrifft Mails mit `@font-face`) — offen, 2026-10-18
- [ ] **PyPDF2 → pypdf** in Tests migrieren (DeprecationWarning) — offen, 2026-10-18
- [ ] **Thread-Deduplizierung ist nicht aktiv:** `filter_thread_superseded()` existiert in `main.py`, wird in `process_emails()` aber nicht aufgerufen → ältere Glieder eines Threads bekommen trotzdem ein PDF. Klären, ob gewollt; ggf. einbinden (nur Auftrag `ablage`) — offen, 2026-10-27
- [ ] **Doppelte PDFs nach Teilfehler:** Scheitert `move_email` nach geschriebenem PDF, bleibt die Mail im Quellordner und erzeugt im nächsten Lauf (Task alle 15 Min.) ein zweites PDF (`_2`). Beobachten — offen, 2026-10-27
- [ ] **correspondence_cleanup automatisch nach dem Archiver** (Tool 1 + 2) — offen, 2026-10-27
- [ ] **Belege automatisch erkennen** statt manuell in `01 für Belege` (KI-Sortierung, datahub DH-043) — offen, 2026-10-27

---

## Erledigt

### Setup & Konfiguration
- [x] **Zielordner auf Netzlaufwerk** `\\HAUSERVER\Dataserver\_datahub\Sammelordner\Korrespondenz` (2026-10-18)
- [x] **`run_archiver.ps1`** — PowerShell-Startskript (2026-07-13)
- [x] **`README.md` ausgebaut** (2026-07-10) — Projektbeschreibung, Installation, Konfiguration, correspondence_cleanup-Kompatibilität
- [x] **Projektstruktur initialisiert** (2026-06-12, Commit `ff5b1eb`)
- [x] **`requirements.txt`** — Abhängigkeiten gepflegt: weasyprint → xhtml2pdf → playwright (2026-06 bis 2026-07)
- [x] **`config/config.ini.template` korrigiert** (2026-06-12) — vollständige [imap]/[output]/[logging]-Struktur
- [x] **SPECIFICATION.md** ausgearbeitet — vollständige Anforderungen, Architektur, Implementierungshinweise
- [x] **CHANGELOG.md, TODO.md, CLAUDE.md** angelegt (2026-06-12)

### Implementierung
- [x] **`src/utils.py`** implementiert (2026-06-12)
- [x] **`src/imap_client.py`** implementiert (2026-06-12)
- [x] **`src/converter.py`** implementiert und mehrfach überarbeitet (2026-06-12 bis 2026-07-13)
- [x] **`src/main.py`** implementiert (2026-06-12)
- [x] **Ordnerstruktur** angelegt: `src/`, `tests/`, `logs/`, `data/` (2026-06-12)

### HTML→PDF-Engine & PDF-Qualität
- [x] **Fix: Fließtext fehlte bei Webfont-Mails** (2026-10-18, `f163b88`) — Warten auf `document.fonts.ready` vor `page.pdf()`
- [x] **Fix: Meta-Header gegen Email-CSS absichern** (2026-10-18, `af8183c`)
- [x] **Playwright-Migration** (2026-07-13) — xhtml2pdf → Headless Chromium; volle CSS-Unterstützung, korrekte Tabellen-Pagination
- [x] **Fix: Outlook WordSection-Seitenumbruch** (2026-07-13) — `page: auto !important` neutralisiert benannte CSS-Seiten
- [x] **`_resolve_cid_images()`** — Inline-Bilder (cid:-Referenzen) als data:-URIs einbetten (2026-07)
- [x] **Inline-Bilder**: Content-ID-Parts nicht als Dateianhang einbetten (2026-07)
- [x] **xhtml2pdf-Ära** (abgeschlossen, 2026-07-10):
  - Arial-Font-Registrierung via reportlab TTF
  - `_strip_mso_css()`, `_normalize_tables()`, `_unwrap_single_cell_tables()`
  - Fix: negativer availWidth-Crash bei FritzBox-Spacer-Zellen
  - Fix: Inhalt auf 1/4 Seitenbreite gequetscht (fehlende width:100%)
  - Fix: leere erste Seite (single-cell-table als KeepInFrame)

### Verarbeitungslogik
- [x] **Thread-Deduplizierung** (2026-07-13) — neueste Antwort eines Threads wird archiviert, ältere Glieder nur verschoben

### correspondence_cleanup-Kompatibilität
- [x] **Deutsches Datumsformat** (`_format_date_german()`) für Gesendet-Feld (2026-07)
- [x] **Label `Gesendet:` statt `Datum:`** — passend zu correspondence_cleanup Regex (2026-07)
- [x] **`An:`-Feld** im Metadaten-Header ergänzt (2026-07)

### Tests
- [x] **`tests/test_stage1_date_format.py`** — 7 Tests für `_format_date_german()` (2026-07)
- [x] **`tests/test_stage2_pdf_content.py`** — 11 Tests: PDF-Inhalt + Regex-Kompatibilität (2026-07)
- [x] **`tests/test_stage3_endtoend.py`** — 5 Tests: correspondence_cleanup End-to-End (2026-07)
- [x] **`tests/test_stage4_regression.py`** — 21 Tests: CID-Bilder, URL-Blocking (Integration), Anhänge, Dateinamen (2026-07)
