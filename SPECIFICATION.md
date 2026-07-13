# email_archiver — Projektspezifikation

## Projektziel

Python-Skript zur automatischen Archivierung von E-Mails als durchsuchbare PDFs mit eingebetteten Anhängen.
Das Skript verbindet sich per IMAP mit dem Strato-Mailserver, verarbeitet alle E-Mails in einem konfigurierten Quellordner, speichert sie als PDF im Windows-Dateisystem und verschiebt die verarbeiteten E-Mails in einen IMAP-Zielordner.

---

## Anforderungen

### Funktional
- Verbindung zum Strato IMAP-Server (SSL, Port 993)
- Quellordner und Zielordner sind IMAP-Ordner (konfigurierbar in INI)
- Thread-Deduplizierung: von einem E-Mail-Thread im selben Batch wird nur die neueste Antwort als PDF archiviert
- Jede relevante E-Mail wird als einzelne PDF-Datei gespeichert
- PDF-Inhalt ist durchsuchbar (Text-basiert, kein OCR nötig)
- E-Mail-Anhänge werden als eingebettete Dateianlagen in das PDF eingebettet (sichtbar im Büroklammer-Panel des PDF-Readers)
- Nach erfolgreicher Konvertierung: E-Mail per IMAP in den konfigurierten Zielordner verschieben
- Externe URLs werden während der PDF-Erzeugung blockiert (Datenschutz / Tracking-Schutz)
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
- `2026-07-10_12-43_Steinel_Oliver.pdf`

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
| INI lesen | `configparser` | stdlib |
| Dateipfade | `pathlib` | stdlib |
| Logging | `logging` | stdlib |
| HTML → PDF | `playwright` (Chromium) | `pip install playwright && playwright install chromium` |
| PDF-Anhänge einbetten | `pikepdf` | `pip install pikepdf` |
| Zeitzone | `zoneinfo` | stdlib (Python 3.9+) |
| Utilities | `ahlib` | `pip install git+https://github.com/Drahmue/ahlib.git` |

### requirements.txt

```
pikepdf
imapclient
playwright
git+https://github.com/Drahmue/ahlib.git
```

### Ordnerstruktur

```
email_archiver/
├── src/
│   ├── main.py           # Einstiegspunkt, Thread-Deduplizierung
│   ├── imap_client.py    # IMAP-Verbindung, E-Mails abrufen, verschieben
│   ├── converter.py      # EML → PDF (Playwright + pikepdf)
│   └── utils.py          # Dateiname sanitisieren, MIME-Header dekodieren
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
├── run_archiver.ps1
├── requirements.txt
├── README.md
├── CHANGELOG.md
├── TODO.md
├── CLAUDE.md
└── SPECIFICATION.md
```

### Verarbeitungsablauf pro Batch

```
1. IMAP: Alle E-Mails aus source_folder abrufen
2. Thread-Deduplizierung (main.py):
   - References/In-Reply-To-Header aller E-Mails auswerten
   - E-Mails, deren Message-ID von einer anderen im Batch referenziert wird → kein PDF
   - Überholte E-Mails werden trotzdem nach processed_folder verschoben
3. Pro E-Mail (zu verarbeiten):
   a. Body extrahieren (_extract_body): bevorzugt text/html, Fallback text/plain in <pre>
   b. cid:-Inline-Bilder als base64 data:-URIs einbetten (_resolve_cid_images)
   c. Metadaten-Header-Block aufbauen (Von / An / Betreff / Gesendet in deutschem Format)
   d. Print-CSS injizieren (inkl. page:auto !important für Outlook WordSection)
   e. Playwright: page.set_content() → page.pdf() (A4, 1–1.5 cm Ränder)
      - Externe URLs (http/https/protokoll-relativ) via page.route() blockiert
      - data:-URIs werden intern verarbeitet, nicht blockiert
   f. PDF in output_folder speichern (Dateiname nach Konvention)
   g. Anhänge extrahieren (_extract_attachments):
      - Parts mit Content-ID überspringen (Inline-Bilder bereits im PDF-Body)
   h. pikepdf: Anhänge als EmbeddedFile einbetten
   i. IMAP: E-Mail in processed_folder verschieben (IMAP MOVE oder COPY+DELETE)
   j. Log-Eintrag: Erfolg mit Dateiname
```

### Fehlerbehandlung

```
- Exception pro E-Mail: logging.error() mit Subject + Traceback
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

## Implementierungshinweise

### IMAP-Ordnernamen mit Umlauten
`imapclient` behandelt die modified-UTF-7-Kodierung (RFC 3501) von Ordnernamen automatisch.

### Playwright HTML→PDF
- Browser-Singleton mit atexit-Cleanup (`_get_browser()` / `_shutdown_browser()`)
- `page.route("**/*", handler)` fängt `data:`-URIs **nicht** ab — sie werden intern verarbeitet
- Nur `http://`, `https://`, `//` blockieren; alle anderen Schemata durchlassen
- Outlook-HTML enthält `div.WordSection1 { page: WordSection1; }` — Chromium fügt dabei
  einen Seitenumbruch ein; Fix: `div[class*='WordSection'] { page: auto !important; }`
- pypdf2 extrahiert Chromium-Ligaturen (z.B. `ff`) manchmal mit Leerzeichen → `\s*` im Regex

### pikepdf Anhänge einbetten
```python
with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
    filespec = AttachedFileSpec(pdf, data, description=filename, filename=filename)
    pdf.attachments[filename] = filespec
    pdf.save(pdf_path)
```
Lesen: `pdf.attachments[name].get_file().read_bytes()` (nicht `.read_bytes()` direkt).

### IMAP MOVE-Befehl
Strato unterstützt IMAP MOVE (RFC 6851). Fallback: COPY + STORE \Deleted + EXPUNGE.

### Thread-Deduplizierung
Outlook und Thunderbird zitieren bei jedem Reply die gesamte Vorgeschichte im Body.
Eine E-Mail gilt als überholt, wenn ihre `Message-ID` im `References`- oder `In-Reply-To`-Header
einer anderen E-Mail im selben Batch auftaucht. Nur Blätter des Thread-Baums erhalten ein PDF.

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
