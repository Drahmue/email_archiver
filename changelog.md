# Changelog — email_archiver

Alle wesentlichen Änderungen am Projekt werden hier dokumentiert.
Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

---

## [Unreleased]

### Geändert
- `SPECIFICATION.md` überarbeitet (nicht committed) — Details zu Dateinamenskonvention, Bibliotheksauswahl (weasyprint + pikepdf), Verarbeitungsablauf und Implementierungshinweisen ergänzt
- `requirements.txt` korrigiert — falschen Standard-Template-Inhalt (numpy/pandas/openpyxl/yfinance) ersetzt durch projektspezifische Abhängigkeiten: weasyprint, pikepdf, imapclient, ahlib
- `config/config.ini.template` korrigiert — generischen Platzhalter ersetzt durch vollständige [imap]/[output]/[logging]-Struktur gemäß SPECIFICATION.md

---

## [0.1.0] - 2026-06-12

### Hinzugefügt
- **Projektstruktur initialisiert** (Commit `ff5b1eb`)
  - `SPECIFICATION.md` — vollständige Projektspezifikation: IMAP-Verbindung zu Strato, E-Mail-zu-PDF-Konvertierung mit weasyprint, Anhänge einbetten mit pikepdf, Dateinamenskonvention, Fehlerbehandlung, Logging
  - `README.md` — minimale Projektbeschreibung (Platzhalter, noch auszubauen)
  - `requirements.txt` — Abhängigkeiten aus Standard-Template (**noch anzupassen**, siehe Bekannte Probleme)
  - `config/config.ini.template` — generische Konfigurationsvorlage aus Standard-Template (**noch anzupassen**, siehe Bekannte Probleme)
  - `.gitignore` — schließt `*.ini`, `logs/`, `.venv/`, `data/` aus dem Repository aus
  - `Python_Standard_Prompt.md` — Referenz-Prompt mit Coding-Standards des Entwicklers (ahlib, Logging, Struktur)
  - `.venv/` — virtuelle Python-Umgebung (lokal, nicht im Repository)

### Begründung
Projekt ersetzt das Outlook-Add-in "Sperry Software Save as PDF" durch eine vollautomatische IMAP-basierte Lösung. Initialer Setup durch automatisiertes Skript auf Basis des Standard-Prompts des Entwicklers.

### Bekannte Probleme im initialen Setup
- `requirements.txt` enthält numpy/pandas/openpyxl/yfinance aus dem Standard-Template — nicht korrekt für dieses Projekt (benötigt werden: weasyprint, pikepdf, imapclient)
- `config/config.ini.template` enthält generischen Platzhalter statt der tatsächlichen [imap]- und [output]-Struktur gemäß SPECIFICATION.md
