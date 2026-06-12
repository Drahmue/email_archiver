# CLAUDE.md — Projektgedächtnis für email_archiver

Diese Datei fasst alle wichtigen Kontextinformationen für Claude zusammen,
damit jede neue Sitzung direkt produktiv starten kann.

---

## Projektziel

Python-Skript zur automatischen Archivierung von E-Mails als durchsuchbare PDFs.
Ersetzt das Outlook-Add-in "Sperry Software Save as PDF" durch eine vollautomatische
IMAP-basierte Lösung (kein Outlook erforderlich).

- IMAP-Server: Strato (imap.strato.de, SSL, Port 993)
- Account: ah@haunschild-family.de
- Quellordner: `01 für Ablage` → nach Verarbeitung nach `01 für Ablage erledigt`
- Ausgabe: PDFs in `C:\Users\ah\Downloads\email_archive`

---

## Entwickler & Umgebung

- Entwickler: ah / Drahmue (GitHub: Drahmue)
- OS: Windows 11 Pro
- Python: 3.12.10
- Shell: bash (Git Bash / WSL)
- Arbeitsverzeichnis: `C:\Users\ah\Dev\email_archiver`

---

## Coding-Standards (aus Python_Standard_Prompt.md)

- **ahlib** verwenden: `from ahlib import screen_and_log, StructuredConfigParser, setup_logging, get_timestamp`
  - Installation: `pip install git+https://github.com/Drahmue/ahlib.git`
- `screen_and_log()` statt `print()` für alle Ausgaben
- `StructuredConfigParser` statt `configparser`
- `setup_logging()` für Log-Initialisierung
- Nur `pathlib.Path` für Dateipfade
- Netzlaufwerke immer als UNC-Pfade
- Modularer Aufbau: kein Code direkt im Hauptprogramm außer Funktionsaufrufen
- Ausführliche Docstrings (Beschreibung, Args, Returns, Raises)
- Type Hints für alle Funktionen
- UTF-8 durchgehend

---

## Technische Kernentscheidungen (aus SPECIFICATION.md)

| Aufgabe | Bibliothek | Hinweis |
|---------|-----------|---------|
| IMAP | `imapclient` | Vereinfacht UTF-7-Kodierung von Ordnernamen mit Umlauten |
| HTML → PDF | `weasyprint` | Externe URLs via eigenen `url_fetcher` blockieren (Sicherheit) |
| PDF-Anhänge einbetten | `pikepdf` | `AttachedFileSpec` — sichtbar im Büroklammer-Panel (Adobe, PDF-XChange) |
| Zeitzone | `zoneinfo` | Europe/Berlin, UTC-Konvertierung aus Date-Header |

### PDF-Dateinamenskonvention
Format: `YYYY-MM-DD_HH-MM_Absender.pdf`
- Datum/Uhrzeit aus `Date:`-Header, lokalisiert auf Europe/Berlin
- Absender: zuerst Display Name, sonst E-Mail-Adresse
- Sonderzeichen/Leerzeichen/Umlaute → Unterstriche
- Max. 60 Zeichen für Absender-Teil
- Namenskollision: Suffix `_2`, `_3`, ...

### Verarbeitungsablauf
1. E-Mail aus source_folder abrufen
2. HTML-Part extrahieren (Fallback: text/plain in HTML wrappen)
3. weasyprint: HTML → PDF
4. Anhänge extrahieren und via pikepdf einbetten
5. PDF speichern
6. E-Mail per IMAP MOVE in processed_folder verschieben
7. Log-Eintrag

### Fehlerbehandlung
- Exception pro E-Mail → `logging.error()` mit Subject + Message-ID + Traceback
- E-Mail bleibt im source_folder, Skript läuft mit nächster weiter
- Abschluss-Zusammenfassung: "X erfolgreich, Y Fehler"

---

## Projektstruktur (Soll-Zustand laut SPECIFICATION.md)

```
email_archiver/
├── src/
│   ├── main.py           # Einstiegspunkt
│   ├── imap_client.py    # IMAP-Verbindung, E-Mails abrufen, verschieben
│   ├── converter.py      # EML → PDF (weasyprint + pikepdf)
│   └── utils.py          # Dateiname sanitisieren, Logging-Setup
├── tests/
├── config/
│   ├── config.ini        # Zugangsdaten (nicht im Repo, in .gitignore)
│   └── config.ini.template
├── logs/
├── data/
├── requirements.txt
├── README.md
├── CHANGELOG.md
├── TODO.md
├── CLAUDE.md
└── SPECIFICATION.md
```

**Aktueller Stand (2026-06-12):** Nur Grundgerüst vorhanden — `src/`, `tests/`, `logs/` fehlen noch, kein Python-Code implementiert.

---

## Bekannte Probleme / Fallstricke

- `requirements.txt` enthält falsche Abhängigkeiten (numpy/pandas statt weasyprint/pikepdf) — muss korrigiert werden
- `config/config.ini.template` ist noch ein generischer Platzhalter — muss auf IMAP-Struktur angepasst werden
- Strato IMAP: Ordnernamen mit Umlauten brauchen modified UTF-7 (RFC 3501) — `imapclient` vereinfacht das
- weasyprint: externe Ressourcen in HTML-E-Mails müssen geblockt werden (Sicherheit / Datenschutz)

---

## Wichtige Dateien

| Datei | Zweck |
|-------|-------|
| `SPECIFICATION.md` | Vollständige Anforderungs- und Architekturdokumentation |
| `Python_Standard_Prompt.md` | Coding-Standards des Entwicklers (Referenz) |
| `CHANGELOG.md` | Versionshistorie mit Begründungen |
| `TODO.md` | Offene und erledigte Aufgaben |
| `config/config.ini.template` | Konfigurationsvorlage (ohne sensible Daten) |

---

## Verwandte Projekte

- Übergeordnetes Nextcloud-Projekt: `C:\Users\ah\Dropbox\ClaudeWork\nextcloud\`
- ahlib (Entwickler-eigene Utility-Bibliothek): https://github.com/Drahmue/ahlib
