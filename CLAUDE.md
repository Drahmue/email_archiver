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

## Technische Kernentscheidungen

| Aufgabe | Bibliothek | Hinweis |
|---------|-----------|---------|
| IMAP | `imapclient` | Vereinfacht UTF-7-Kodierung von Ordnernamen mit Umlauten |
| HTML → PDF | `playwright` (Chromium) | Headless Chromium via sync_playwright; volle CSS-Unterstützung |
| PDF-Anhänge einbetten | `pikepdf` | `AttachedFileSpec` — sichtbar im Büroklammer-Panel (Adobe, PDF-XChange) |
| Zeitzone | `zoneinfo` | Europe/Berlin, UTC-Konvertierung aus Date-Header |

### Konvertierungs-Pipeline (converter.py)
1. **`_extract_body(msg)`** — HTML-Part extrahieren (Fallback: text/plain in `<pre>`)
2. **`_resolve_cid_images(msg, html)`** — Ersetzt `cid:`-Referenzen durch base64-`data:`-URIs (Inline-Bilder in multipart/related)
3. Metadaten-Header-Block + Druck-CSS in HTML injizieren
4. Playwright: `page.set_content()` → `page.pdf()` (A4, 1–1.5 cm Ränder)
   - Externe URLs (`http://`, `https://`, `//`) via `page.route()` geblockt

### PDF-Metadaten-Block
Jedes PDF beginnt mit einem sichtbaren Kopfblock (für correspondence_cleanup):
```
Von:      Absender (RFC-2822-Format)
An:       Empfänger
Betreff:  Betreff
Gesendet: 3. Juli 2026  ← deutsches Langformat, Europe/Berlin
```
Wichtig: Label `Gesendet:` (nicht `Datum:`), `An:`-Feld vorhanden — correspondence_cleanup-Regex erfordert das.

### PDF-Dateinamenskonvention
Format: `YYYY-MM-DD_HH-MM_Absender.pdf`
- Datum/Uhrzeit aus `Date:`-Header, lokalisiert auf Europe/Berlin
- Absender: zuerst Display Name, sonst E-Mail-Adresse
- Sonderzeichen/Leerzeichen/Umlaute → Unterstriche
- Max. 60 Zeichen für Absender-Teil
- Namenskollision: Suffix `_2`, `_3`, ...

### Verarbeitungsablauf
1. E-Mail aus source_folder abrufen
2. HTML-Part extrahieren (Fallback: text/plain in `<pre>`)
3. `_resolve_cid_images`: cid:-Referenzen → base64-data:-URIs
4. Metadaten-Header-Block (Von/An/Betreff/Gesendet) einfügen
5. Playwright/Chromium: HTML → PDF (externe URLs auf Netzwerkebene blockiert)
6. PDF speichern
7. Anhänge extrahieren (Parts mit Content-ID überspringen — bereits im Body gerendert!)
8. pikepdf: Anhänge als EmbeddedFile einbetten
9. E-Mail per IMAP MOVE in processed_folder verschieben
10. Log-Eintrag

### Fehlerbehandlung
- Exception pro E-Mail → `logging.error()` mit Subject + Message-ID + Traceback
- E-Mail bleibt im source_folder, Skript läuft mit nächster weiter
- Abschluss-Zusammenfassung: "X erfolgreich, Y Fehler"

---

## Projektstruktur (aktueller Stand, 2026-07-10)

```
email_archiver/
├── src/
│   ├── main.py           # Einstiegspunkt
│   ├── imap_client.py    # IMAP-Verbindung, E-Mails abrufen, verschieben
│   ├── converter.py      # EML → PDF (xhtml2pdf + pikepdf + BeautifulSoup)
│   └── utils.py          # Dateiname sanitisieren, MIME-Header dekodieren
├── tests/
│   ├── test_stage1_date_format.py    # 7 Tests: _format_date_german()
│   ├── test_stage2_pdf_content.py    # 11 Tests: PDF-Inhalt + Regex-Compat.
│   ├── test_stage3_endtoend.py       # 5 Tests: correspondence_cleanup E2E
│   └── test_stage4_regression.py     # 21 Tests: CID, URL-Blockierung (Integration), Anhänge, Dateinamen
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

---

## Bekannte Fallstricke / Playwright-Eigenheiten

- `page.route("**/*", handler)` fängt `data:`-URIs **nicht** ab — sie werden intern verarbeitet. Nur `http://`/`https://`/`//` blockieren.
- `page.pdf()` benötigt Headless-Chromium; `headless=True` ist der Default bei `chromium.launch()`.
- pypdf2 extrahiert Chromium-PDF-Ligaturen (z.B. `ff`, `fi`) manchmal mit eingeschobenem Leerzeichen → bei PDF-Textextraktion `\s*` zwischen Ligaturzeichen im Regex verwenden.
- Inline-Bilder (Content-ID): nicht als pikepdf-Anhang einbetten — sie sind bereits als data:-URI im HTML-Body gerendert.
- pikepdf API: `pdf.attachments[name].get_file().read_bytes()` (nicht `.read_bytes()` direkt)

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

- correspondence_cleanup: `C:\Users\ah\Dev\correspondence_cleanup\correspondence_cleanup_1_email.py`
  — verarbeitet die erzeugten PDFs weiter (Umbenennen nach Absender/Datum/Betreff)
- ahlib (Entwickler-eigene Utility-Bibliothek): https://github.com/Drahmue/ahlib
