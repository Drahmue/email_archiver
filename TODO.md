# TODO — email_archiver

---

## Offen

### Korrekturen am initialen Setup

- [x] **`requirements.txt` korrigiert** (2026-06-12) — weasyprint, pikepdf, imapclient, ahlib
- [x] **`config/config.ini.template` korrigiert** (2026-06-12) — vollständige [imap]/[output]/[logging]-Struktur

- [ ] **`README.md` ausbauen** — derzeit nur Platzhalter; Projektbeschreibung, Installation, Konfiguration und Verwendung ergänzen

### Implementierung (noch keine Source-Dateien vorhanden)

- [ ] **`src/utils.py`** implementieren
  - `setup_logging()` — RotatingFileHandler + Konsole, Format wie in SPECIFICATION
  - `sanitize_filename()` — Sonderzeichen/Umlaute → Unterstriche, max. 60 Zeichen, Kollisionsauflösung mit Suffix `_2`, `_3`, ...
  - `build_pdf_filename()` — Datum/Uhrzeit aus Date-Header, Europe/Berlin-Zeitzone

- [ ] **`src/imap_client.py`** implementieren
  - IMAP-Verbindung zu Strato (SSL, Port 993) via `imapclient`
  - Ordnernamen mit Umlauten korrekt in modified UTF-7 kodieren (RFC 3501)
  - E-Mails aus `source_folder` abrufen
  - E-Mail nach Verarbeitung in `processed_folder` verschieben (IMAP MOVE, Fallback: COPY + DELETE)

- [ ] **`src/converter.py`** implementieren
  - E-Mail parsen: HTML-Part bevorzugt, Fallback auf text/plain (in HTML wrappen)
  - Externe URLs in HTML blockieren (eigener `url_fetcher` für weasyprint — Sicherheit)
  - HTML → PDF via weasyprint (UTF-8, base64-Inline-Bilder werden unterstützt)
  - Anhänge extrahieren (alle Parts außer text/* und multipart/*)
  - Anhänge via pikepdf als EmbeddedFile ins PDF einbetten (sichtbar im Büroklammer-Panel)

- [ ] **`src/main.py`** implementieren
  - Einstiegspunkt: Konfiguration laden, IMAP verbinden, E-Mails verarbeiten
  - Fehlerbehandlung pro E-Mail: Fehler loggen, E-Mail im source_folder belassen, weitermachen
  - Abschluss-Zusammenfassung im Log (X erfolgreich, Y Fehler)

- [ ] **Ordnerstruktur anlegen**
  - `src/` — noch nicht vorhanden
  - `tests/` — noch nicht vorhanden
  - `logs/` — noch nicht vorhanden (bereits in .gitignore)
  - `data/` — noch nicht vorhanden (bereits in .gitignore)

### Tests

- [ ] **`tests/test_utils.py`** — Unit-Tests für Dateinamens-Sanitisierung und Kollisionsauflösung
- [ ] **`tests/test_converter.py`** — Test mit Beispiel-EML-Dateien (HTML, plain-text, mit/ohne Anhänge)
- [ ] **`tests/test_imap_client.py`** — Integrations-/Mocktest für IMAP-Operationen

---

## Erledigt

- [x] **Projektstruktur initialisiert** (2026-06-12, Commit `ff5b1eb`)
  - Repository angelegt, `.gitignore`, `SPECIFICATION.md`, `README.md`, `requirements.txt`, `config/config.ini.template`, `.venv/`
- [x] **SPECIFICATION.md** ausgearbeitet — vollständige Anforderungen, Architektur, Implementierungshinweise
- [x] **CHANGELOG.md** angelegt (2026-06-12)
- [x] **TODO.md** angelegt (2026-06-12)
- [x] **CLAUDE.md** angelegt (2026-06-12)
