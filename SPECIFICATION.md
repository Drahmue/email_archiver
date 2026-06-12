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
| IMAP-Verbindung | `imaplib` | stdlib |
| E-Mail parsen | `email` | stdlib |
| INI lesen | `configparser` | stdlib |
| Dateipfade | `pathlib` | stdlib |
| Logging | `logging` | stdlib |
| HTML → PDF | `weasyprint` | `pip install weasyprint` |
| PDF-Anhänge einbetten | `pikepdf` | `pip install pikepdf` |
| Zeitzone | `zoneinfo` | stdlib (Python 3.9+) |

### requirements.txt

```
weasyprint
pikepdf
```

### Ordnerstruktur

```
email_archiver/
├── src/
│   ├── main.py           # Einstiegspunkt
│   ├── imap_client.py    # IMAP-Verbindung, E-Mails abrufen, verschieben
│   ├── converter.py      # EML → PDF (weasyprint + pikepdf)
│   └── utils.py          # Dateiname sanitisieren, Logging-Setup
├── tests/
├── config/
│   ├── config.ini        # Zugangsdaten (nicht im Repo)
│   └── config.ini.template
├── logs/
├── data/
├── requirements.txt
├── README.md
├── changelog.md
└── SPECIFICATION.md
```

### Verarbeitungsablauf pro E-Mail

```
1. IMAP: E-Mail aus source_folder abrufen (UNSEEN oder ALL — konfigurierbar)
2. email.message_from_bytes() → Message-Objekt
3. Body extrahieren:
   - Bevorzugt: text/html Part
   - Fallback: text/plain Part (in einfaches HTML wrappen)
4. weasyprint: HTML → PDF (bytes)
5. Anhänge extrahieren (alle Parts außer text/* und multipart/*)
6. pikepdf: Anhänge als EmbeddedFile in das PDF einbetten
   - Jeder Anhang mit originalem Dateinamen
   - Sichtbar im Büroklammer-Panel (Adobe, PDF-XChange, etc.)
7. PDF in output_folder speichern (Dateiname nach Konvention)
8. IMAP: E-Mail in processed_folder verschieben (IMAP MOVE oder COPY+DELETE)
9. Log-Eintrag: Erfolg mit Dateiname
```

### Fehlerbehandlung

```
- Exception pro E-Mail: logging.error() mit Subject + Message-ID + Traceback
- E-Mail bleibt im source_folder (wird nicht verschoben)
- Skript läuft mit nächster E-Mail weiter
- Am Ende: Zusammenfassung im Log (X erfolgreich, Y Fehler)
```

---

## Logging

- Log-Datei: `logs/email_archiver.log` (rotating, max 5 MB, 3 Backups)
- Konsole: gleichzeitig ausgeben
- Format: `2026-06-11 14:30:15 [INFO] Verarbeite: "Betreff" von Absender`

---

## Implementierungshinweise

### IMAP-Ordnernamen mit Umlauten
Strato-IMAP verwendet UTF-7 kodierte Ordnernamen. Python `imaplib` erwartet die Ordnernamen
in modifiziertem UTF-7 (RFC 3501). Falls Umlaute im Ordnernamen auftreten (`ü`, `ä`, etc.),
müssen diese korrekt kodiert werden. Library `imapclient` (optional) vereinfacht dies:
```
pip install imapclient
```
Alternativ: `imaplib` direkt mit manueller UTF-7-Kodierung.

### weasyprint HTML-Rendering
- Inline-Bilder (base64 data URIs) werden unterstützt — kein Problem
- Externe Ressourcen (URLs in HTML-E-Mails): blockieren via `url_fetcher` (Sicherheit)
- Zeichensatz: UTF-8 explizit setzen (`<meta charset="utf-8">` in HTML-Wrapper)

### pikepdf Anhänge einbetten
```python
import pikepdf
from pikepdf import AttachedFileSpec, Name

with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
    for filename, data in attachments:
        filespec = AttachedFileSpec.from_obj(
            pdf, data, description=filename
        )
        pdf.attachments[filename] = filespec
    pdf.save(pdf_path)
```

### IMAP MOVE-Befehl
Strato unterstützt IMAP MOVE (RFC 6851). Fallback: COPY + STORE \Deleted + EXPUNGE.

---

## Bekannte Referenzen

- GitHub: `perroneclaudio/eml-to-pdf-converter-embedder` — ähnlicher Ansatz, kein INI, kein IMAP
- pikepdf Doku: https://pikepdf.readthedocs.io/en/latest/topics/attachments.html

---

## Projektkontext

- Entwickler: ah (ahmain, Windows 11)
- Zweck: Ersatz für Sperry Software "Save as PDF" (Outlook Add-in) — vollautomatisch statt manuell
- Ziel-E-Mail-Account: ah@haunschild-family.de (Strato IMAP)
- E-Mail-Client: Thunderbird (ahmain) — Skript läuft unabhängig davon via IMAP direkt
- Ausgabe-PDFs landen in Windows-Ordner (z.B. für manuelle Ablage oder weitere Automatisierung)
- Teil des übergeordneten Nextcloud-Projekts (`C:\Users\ah\Dropbox\ClaudeWork\nextcloud\`)
