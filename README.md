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
3. Pro E-Mail:
   - HTML-Body extrahieren (Fallback: plain-text)
   - HTML vorverarbeiten: MSO-CSS entfernen, Tabellen normalisieren, cid:-Bilder auflösen
   - Metadaten-Header einbetten (Von / An / Betreff / Gesendet)
   - PDF erzeugen via xhtml2pdf
   - Dateianhänge als EmbeddedFile in die PDF einbetten (pikepdf)
   - PDF speichern unter `JJJJ-MM-TT_HH-MM_Absender.pdf`
4. E-Mail in `processed_folder` verschieben
5. Fehler werden geloggt, Verarbeitung läuft weiter

### PDF-Dateiname

```
JJJJ-MM-TT_HH-MM_Vorname_Nachname.pdf
Beispiel: 2026-07-09_15-45_Steinel_Oliver.pdf
```

Datum und Uhrzeit aus dem E-Mail-Header (`Date:`), Zeitzone Europe/Berlin.

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Konfiguration

`config/config.ini` (aus `config/config.ini.template` anlegen):

```ini
[imap]
server           = imap.strato.de
port             = 993
username          = name@domain.de
password          = geheim
source_folder    = 01 für Ablage
processed_folder = 01 für Ablage erledigt

[output]
folder = C:\Users\...\Downloads\email_archive

[logging]
level = INFO
```

## Verwendung

```bash
python src/main.py
```

Log wird unter `logs/email_archiver_JJJJMMTT_HHMMSS.log` gespeichert.

## Requirements

- Python 3.11+
- Windows (Zeitzone Europe/Berlin via `zoneinfo`)
- Pakete: `xhtml2pdf`, `beautifulsoup4`, `pikepdf`, `imapclient`, `ahlib`

## Kompatibilität mit correspondence_cleanup

Die erzeugten PDFs enthalten einen Metadaten-Header-Block mit den Labels
`Von:`, `An:`, `Betreff:`, `Gesendet:` — genau die Felder, die `correspondence_cleanup_1_email.py`
via Regex aus dem PDF-Text extrahiert. Das Datumsformat im `Gesendet:`-Feld ist deutsches
Langformat (`3. Juli 2026`), passend zum Datumsparser von correspondence_cleanup.
