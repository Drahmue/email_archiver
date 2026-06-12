# TODO — email_archiver

---

## Offen

### Korrekturen am initialen Setup

- [x] **`requirements.txt` korrigiert** (2026-06-12) — weasyprint, pikepdf, imapclient, ahlib
- [x] **`config/config.ini.template` korrigiert** (2026-06-12) — vollständige [imap]/[output]/[logging]-Struktur

- [ ] **`README.md` ausbauen** — derzeit nur Platzhalter; Projektbeschreibung, Installation, Konfiguration und Verwendung ergänzen

### Implementierung

- [x] **`src/utils.py`** implementiert (2026-06-12)
- [x] **`src/imap_client.py`** implementiert (2026-06-12)
- [x] **`src/converter.py`** implementiert (2026-06-12)
- [x] **`src/main.py`** implementiert (2026-06-12)
- [x] **Ordnerstruktur** angelegt: `src/`, `tests/`, `logs/`, `data/` (2026-06-12)

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
