# email_archiver — Projektspezifikation

## Projektziel

Python-Skript zur automatischen Archivierung von E-Mails als durchsuchbare PDFs mit eingebetteten Anhängen.
Das Skript verbindet sich per IMAP mit dem Strato-Mailserver, verarbeitet alle E-Mails in einem konfigurierten Quellordner, speichert sie als PDF im Windows-Dateisystem und verschiebt die verarbeiteten E-Mails in einen IMAP-Zielordner.

---

## Anforderungen

### Funktional
- Verbindung zum Strato IMAP-Server (SSL, Port 993)
- Quellordner und Zielordner sind IMAP-Ordner (konfigurierbar in INI)
- Jede E-Mail wird als einzelne PDF-Datei gespeichert
- PDF-Inhalt ist durchsuchbar (Text-basiert, kein OCR nötig — E-Mail-Text ist bereits Text)
- E-Mail-Anhänge werden als eingebettete Dateianlagen in das PDF eingebettet (sichtbar im Büroklammer-Panel des PDF-Readers, z.B. Adobe Acrobat oder PDF-XChange)
- Nach erfolgreicher Konvertierung: E-Mail per IMAP in den konfigurierten Zielordner verschieben
- Fehlerbehandlung: fehlerhafte E-Mails überspringen, Fehler ins Log schreiben, mit nächster E-Mail weitermachen
- Alle Pfade und Zugangsdaten in `config/config.ini` (nicht im Code)

### Nicht im Scope
- Outlook / Office 365 — nur Strato IMAP
- OCR (E-Mail-Text ist bereits maschinenlesbar)
- GUI
- Scheduler (Skript wird manuell oder per Windows Task Scheduler gestartet)

---

## Konfiguration (`config/config.ini`)

```ini
[imap]
server           = imap.strato.de
port             = 993
username         = ah@haunschild-family.de
password         = PASSWORT_HIER_EINTRAGEN
source_folder    = 01 für Ablage
processed_folder = 01 für Ablage erledigt

[output]
folder = C:\Users\ah\Downloads\email_archive

[logging]
log_level = INFO
```

**Hinweis:** `config.ini` ist in `.gitignore` — niemals ins Repository einchecken.
Im Repository liegt nur `config/config.ini.template` ohne Zugangsdaten.

---

## Dateinamenskonvention (PDF-Ausgabe)

Format: `YYYY-MM-DD_HH-MM_Absender.pdf`

Beispiele:
- `2026-06-11_14-30_noreply@example.com.pdf`
- `2026-06-11_09-15_Max_Mustermann.pdf`

Regeln:
- Datum und Uhrzeit aus dem `Date:`-Header der E-Mail (UTC → lokale Zeit Europe/Berlin)
- Absender: zuerst Display Name (falls vorhanden), sonst E-Mail-Adresse
- Sonderzeichen, Leerzeichen, Umlaute im Absender → Unterstriche ersetzen
- Maximale Länge des Absender-Teils: 60 Zeichen (abschneiden falls länger)
- Bei Namenskollision (gleicher Dateiname bereits vorhanden): Suffix `_2`, `_3`, ... anhängen

---

## Technische Architektur

### Bibliotheken

| Zweck | Library | Installation |
|-------|---------|-------------|
| IMAP-Verbindung | `imapclient` | `pip install imapclient` |
| E-Mail parsen | `email` | stdlib |
| HTML parsen/transformieren | `beautifulsoup4` | `pip install beautifulsoup4` |
| INI lesen | `configparser` | stdlib |
| Dateipfade | `pathlib` | stdlib |
| Logging | `logging` | stdlib |
| HTML → PDF | `xhtml2pdf` (pisa) | `pip install xhtml2pdf` |
| Font-Registrierung | `reportlab` | `pip install reportlab` |
| PDF-Anhänge einbetten | `pikepdf` | `pip install pikepdf` |
| Zeitzone | `zoneinfo` | stdlib (Python 3.9+) |

**Hinweis:** `weasyprint` war ursprünglich geplant, wurde aber durch `xhtml2pdf` ersetzt — xhtml2pdf rendert Umlaute korrekt wenn Arial als TTF-Font via reportlab registriert ist.

### requirements.txt

```
imapclient
xhtml2pdf
reportlab
pikepdf
beautifulsoup4
PyPDF2
git+https://github.com/Drahmue/ahlib.git
```

### Ordnerstruktur

```
email_archiver/
├── src/
│   ├── main.py           # Einstiegspunkt
│   ├── imap_client.py    # IMAP-Verbindung, E-Mails abrufen, verschieben
│   ├── converter.py      # EML → PDF (xhtml2pdf + pikepdf)
│   └── utils.py          # Dateiname sanitisieren, Logging-Setup
├── tests/
│   ├── test_stage1_date_format.py   # Unit-Tests _format_date_german()
│   ├── test_stage2_pdf_content.py   # PDF-Inhalt + correspondence_cleanup-Regex
│   ├── test_stage3_endtoend.py      # End-to-End mit correspondence_cleanup
│   └── test_stage4_regression.py    # CID-Bilder, URL-Blocking, Anhänge, Dateinamen
├── config/
│   ├── config.ini        # Zugangsdaten (nicht im Repo)
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

### Verarbeitungsablauf pro E-Mail

```
1. IMAP: E-Mail aus source_folder abrufen
2. email.message_from_bytes() → Message-Objekt
3. Body extrahieren (_extract_body):
   - Bevorzugt: text/html Part
   - Fallback: text/plain Part (in einfaches HTML wrappen)
4. HTML-Vorverarbeitung:
   a. _strip_mso_css()      — @list-CSS-At-Regeln entfernen (brechen xhtml2pdf)
   b. _normalize_tables()   — Outlook-Tabellen normalisieren (Rahmen, Breite)
   c. _resolve_cid_images() — cid:-Referenzen durch base64-data:-URIs ersetzen
5. Metadaten-Header-Block aufbauen (Von / An / Betreff / Gesendet in deutschem Format)
6. Vollständiges HTML-Dokument zusammensetzen (mit Arial-CSS, Meta-Block, Body)
7. xhtml2pdf: HTML → PDF (externe URLs via link_callback blockiert)
8. Anhänge extrahieren (_extract_attachments):
   - Parts mit Content-ID überspringen (Inline-Bilder bereits im PDF-Body)
9. pikepdf: Anhänge als EmbeddedFile in das PDF einbetten
10. PDF in output_folder speichern (Dateiname nach Konvention)
11. IMAP: E-Mail in processed_folder verschieben (IMAP MOVE oder COPY+DELETE)
12. Log-Eintrag: Erfolg mit Dateiname
```

### Fehlerbehandlung

```
- Exception pro E-Mail: logging.error() mit Subject + Message-ID + Traceback
- E-Mail bleibt im source_folder (wird nicht verschoben)
- Skript läuft mit nächster E-Mail weiter
- Am Ende: Zusammenfassung im Log (X erfolgreich, Y Fehler)
```

---

## PDF-Metadaten-Block

Jedes PDF beginnt mit einem sichtbaren Kopfblock (grau unterstrichen), der von
`correspondence_cleanup_1_email.py` per Regex ausgewertet wird:

```
Von:      "Stefan Krammer" <krammer@architektureal.de>
An:       "Dr. A. Haunschild" <ah@haunschild-family.de>
Betreff:  AW: Pläne für Sachverständigen
Gesendet: 3. Juli 2026
```

Regex-Muster von correspondence_cleanup (müssen matchen):
- `Von: (.+)`
- `An: (.+)`
- `Betreff: (.+)`
- `Gesendet:\s*(.+)`
- `\d{1,2}\. \w+ \d{4}` (deutsches Datumsformat)

---

## Tabellen-Normalisierung

Outlook-HTML enthält zwei Typen von Tabellen:

| Typ | Erkennungsmerkmal | Behandlung |
|-----|------------------|------------|
| Datentabelle | `border="1"` (HTML-Attr.) ohne `border:none` im Style | graue 1px-Rahmen, `width:100%` |
| Layout-Tabelle | `border:none` im CSS-Style (auch wenn `border="1"` im HTML-Attr.) | Rahmen auf 0 setzen, Breite nicht ändern |

In beiden Fällen: `width` aus HTML-Attribut und style-String der `<td>`/`<th>` entfernen.

---

## Logging

- Log-Datei: `logs/email_archiver.log` (rotating, max 5 MB, 3 Backups)
- Konsole: gleichzeitig ausgeben
- Format: `2026-06-11 14:30:15 [INFO] Verarbeite: "Betreff" von Absender`

---

## Implementierungshinweise

### IMAP-Ordnernamen mit Umlauten
`imapclient` behandelt die modified-UTF-7-Kodierung (RFC 3501) von Ordnernamen automatisch.
`imaplib` direkt würde manuelle Kodierung erfordern.

### xhtml2pdf HTML-Rendering
- Inline-Bilder als base64 `data:`-URIs werden unterstützt
- Externe Ressourcen (URLs) via `link_callback` blockieren (Datenschutz / Tracking-Schutz)
- Font: Arial TTF via `pdfmetrics.registerFont(TTFont(...))` registrieren — kein `@font-face` nötig
- `border:none` in CSS wird von xhtml2pdf nicht immer korrekt ausgewertet — `border="0"` HTML-Attribut zusätzlich setzen
- `border-collapse:collapse` kombiniert mit impliziten Rahmen erzeugt in xhtml2pdf sichtbare Linien
- `min-width` wird nicht unterstützt — `width:100%` verwenden

### pikepdf Anhänge einbetten
```python
with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
    filespec = AttachedFileSpec(pdf, data, description=filename, filename=filename)
    pdf.attachments[filename] = filespec
    pdf.save(pdf_path)
```
Anhänge sind im Büroklammer-Panel sichtbar (Adobe Acrobat, PDF-XChange).
Lesen: `pdf.attachments[name].get_file().read_bytes()` (nicht `.read_bytes()` direkt).

### IMAP MOVE-Befehl
Strato unterstützt IMAP MOVE (RFC 6851). Fallback: COPY + STORE \Deleted + EXPUNGE.

---

## Bekannte Referenzen

- pikepdf Doku: https://pikepdf.readthedocs.io/en/latest/topics/attachments.html
- correspondence_cleanup: `C:\Users\ah\Dev\correspondence_cleanup\correspondence_cleanup_1_email.py`

---

## Projektkontext

- Entwickler: ah / Drahmue (Windows 11, Python 3.12)
- Zweck: Ersatz für Sperry Software "Save as PDF" (Outlook Add-in) — vollautomatisch statt manuell
- Ziel-E-Mail-Account: ah@haunschild-family.de (Strato IMAP)
- E-Mail-Client: Thunderbird — Skript läuft unabhängig davon via IMAP direkt
- Ausgabe-PDFs werden von `correspondence_cleanup_1_email.py` weiterverarbeitet (Umbenennen/Ablegen)
