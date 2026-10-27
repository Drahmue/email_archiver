# email_archiver

Automatisiertes Tool zum Archivieren von E-Mails aus einem IMAP-Postfach als PDF-Dateien.

## Funktion

Das Tool verbindet sich via IMAP mit dem Postfach, konvertiert jede E-Mail im Quellordner in eine
PDF-Datei und verschiebt sie anschließend in den Zielordner (z. B. "für Ablage erledigt"). Die
erzeugten PDFs sind kompatibel mit der **correspondence_cleanup**-Suite und können von dieser direkt
weiterverarbeitet werden.

### Verarbeitungsablauf

1. IMAP-Verbindung herstellen (Strato, SSL)
2. Alle E-Mails im `source_folder` abrufen
3. Thread-Deduplizierung: E-Mails, die von einer neueren Antwort im selben Batch überholt werden, erhalten kein PDF (werden aber trotzdem in `processed_folder` verschoben)
4. Pro E-Mail:
   - HTML-Body extrahieren (Fallback: plain-text in `<pre>`)
   - Inline-Bilder (`cid:`-Referenzen) als `data:`-URIs einbetten
   - Metadaten-Header einbetten (Von / An / Betreff / Gesendet)
   - PDF erzeugen via Playwright (Headless Chromium) — externe URLs werden blockiert
   - Dateianhänge als EmbeddedFile in die PDF einbetten (pikepdf)
   - PDF speichern unter `JJJJ-MM-TT_HH-MM_Absender.pdf`
5. E-Mail in `processed_folder` verschieben
6. Fehler werden geloggt, Verarbeitung läuft weiter

### PDF-Dateiname

```
JJJJ-MM-TT_HH-MM_Vorname_Nachname.pdf
Beispiel: 2026-07-10_12-43_Steinel_Oliver.pdf
```

Datum und Uhrzeit aus dem E-Mail-Header (`Date:`), Zeitzone Europe/Berlin.

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## Konfiguration

`config/config.ini` (aus `config/config.ini.template` anlegen):

```ini
[imap]
server           = imap.strato.de
port             = 993
username          = name@domain.de
password          =                ; leer lassen, wenn im Schlüsselbund (set_credentials.py)
source_folder    = 01 für Ablage
processed_folder = 01 für Ablage erledigt

[output]
folder = C:\Users\...\Downloads\email_archive

; optional: zweiter Auftrag für Belege-Mails
[belege]
source_folder    = 01 für Belege
processed_folder = 01 für Ablage erledigt
output_folder    = D:\Dataserver\_datahub\belege\eingang

[logging]
level = INFO
```

Passwort: zuerst Windows-Schlüsselbund (Dienst `email_archiver`, Benutzer = IMAP-Benutzer,
anlegen mit `.venv\Scripts\python.exe set_credentials.py` unter dem Konto, unter dem der
Archiver läuft), sonst `[imap] password`.

## Verwendung

```powershell
# PowerShell-Startskript (empfohlen):
.\run_archiver.ps1

# Oder direkt:
python src/main.py
python src/main.py --dry-run     # nur auflisten, nichts schreiben oder verschieben
```

Log wird unter `logs/email_archiver_JJJJ-MM.log` gespeichert (eine Datei pro Monat).

## Betrieb auf dem HauServer

- Installation: `D:\Dataserver\_Batchprozesse\email_archiver`, Chromium im Projektordner
  (`ms-playwright\`, über `PLAYWRIGHT_BROWSERS_PATH` im Startskript)
- Task `\AHSkripts\email_archiver` alle 15 Minuten als Administrator (`task_anlegen.ps1`),
  startet `start_email_archiver.ps1` (git pull, dann `src\main.py`; `-DryRun` möglich)
- Fehler meldet der Task-Watchdog (`max_age_hours` 2)

## Requirements

- Python 3.11+
- Windows (Zeitzone Europe/Berlin via `zoneinfo`)
- Pakete: `playwright`, `pikepdf`, `imapclient`, `ahlib`, `keyring`, `truststore`
- Chromium (via `playwright install chromium`)

## Kompatibilität mit correspondence_cleanup

Die erzeugten PDFs enthalten einen Metadaten-Header-Block mit den Labels
`Von:`, `An:`, `Betreff:`, `Gesendet:` — genau die Felder, die `correspondence_cleanup_1_email.py`
via Regex aus dem PDF-Text extrahiert. Das Datumsformat im `Gesendet:`-Feld ist deutsches
Langformat (`3. Juli 2026`), passend zum Datumsparser von correspondence_cleanup.
