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
| HTML parsen | `beautifulsoup4` | HTML-Attribute manipulieren (Tabellen-Normalisierung) |
| HTML → PDF | `xhtml2pdf` (pisa) | weasyprint hatte Umlaut-Probleme; xhtml2pdf + Arial TTF funktioniert |
| Font-Registrierung | `reportlab` | Arial aus `C:\Windows\Fonts` — Unicode/Umlaut-Support |
| PDF-Anhänge einbetten | `pikepdf` | `AttachedFileSpec` — sichtbar im Büroklammer-Panel (Adobe, PDF-XChange) |
| Zeitzone | `zoneinfo` | Europe/Berlin, UTC-Konvertierung aus Date-Header |

### HTML-Preprocessing-Pipeline (converter.py)
Vor der PDF-Erzeugung wird der HTML-Body durch drei Transformationen geschickt:

1. **`_strip_mso_css(html)`** — Entfernt `@list`-CSS-At-Regeln (Outlook-proprietär, bricht xhtml2pdf-Parser)
2. **`_normalize_tables(html)`** — Normalisiert Outlook-Tabellen:
   - Datentabellen (`border="1"` ohne `border:none` im CSS): schwarze Rahmen → grau, volle Breite
   - Layout-Tabellen (`border:none` im CSS-Style, auch wenn `border="1"` im HTML-Attr.): alle Rahmen auf 0, Breite unverändert
   - In beiden Fällen: `width` aus HTML-Attributen und style-Strings der `<td>`/`<th>` entfernen
3. **`_resolve_cid_images(msg, html)`** — Ersetzt `cid:`-Referenzen durch base64-`data:`-URIs (Inline-Bilder in multipart/related)

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
2. HTML-Part extrahieren (Fallback: text/plain in HTML wrappen)
3. HTML-Preprocessing: `_strip_mso_css` → `_normalize_tables` → `_resolve_cid_images`
4. Metadaten-Header-Block (Von/An/Betreff/Gesendet) einfügen
5. xhtml2pdf: HTML → PDF (externe URLs via link_callback blockiert)
6. Anhänge extrahieren (Parts mit Content-ID überspringen — Inline-Bilder!)
7. pikepdf: Anhänge als EmbeddedFile einbetten
8. PDF speichern
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
│   └── test_stage4_regression.py     # 26 Tests: CID, URLs, Anhänge, Dateinamen
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

## Bekannte Fallstricke / xhtml2pdf-Eigenheiten

- `border:none` in CSS wird von xhtml2pdf nicht zuverlässig ausgewertet → `border="0"` HTML-Attribut zusätzlich setzen
- `border-collapse:collapse` erzeugt in xhtml2pdf sichtbare Linien auch wenn `border:none` im Style
- `min-width` wird nicht unterstützt → `width:100%` verwenden
- Outlook-Muster: `border="1"` + `style="border:none"` = Layout-Tabelle (CSS überschreibt HTML-Attribut in echten Browsern)
- `@list`-CSS-At-Regeln aus Outlook HTML brechen xhtml2pdf → vor PDF-Erzeugung entfernen
- Inline-Bilder (Content-ID): nicht als pikepdf-Anhang einbetten — sie sind bereits im PDF-Body gerendert
- Arial TTF-Font muss via `pdfmetrics.registerFont(TTFont(...))` registriert werden (kein `@font-face`)
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
