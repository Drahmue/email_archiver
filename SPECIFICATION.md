# [Projektname] - Spezifikation für Claude Code

## Projekt-Übersicht

**Projektname:** [Name]  
**Zweck:** [Eine Zeile - was macht das Projekt?]  
**Hauptfunktionen:**
- [Funktion 1]
- [Funktion 2]
- [Funktion 3]

**Zielumgebung:**
- Betriebssystem: [Windows/Linux/macOS]
- Python-Version: [Version]
- Deployment: [Desktop/Server/Cloud]

---

## Voraussetzungen

### System
- [OS-spezifische Anforderungen]
- [Hardware-Anforderungen falls relevant]

### Externe Dependencies
- [Service 1]: [Was wird benötigt? z.B. API-Key, Account]
- [Service 2]: [Was wird benötigt?]

### Benutzer-Setup erforderlich
- [ ] [Setup-Schritt 1 - z.B. Azure Account erstellen]
- [ ] [Setup-Schritt 2]
- [ ] [Setup-Schritt 3]

---

## WICHTIG: Anweisungen für Claude Code

### ⚠️ Diese Instruktionen VOR Code-Generierung lesen!

### Phase 1: Analyse (ZWINGEND vor Implementierung)

**Externe Libraries/Komponenten analysieren:**
```markdown
1. [ ] Analysiere [externe Library/API/Service]
   - Dokumentation lesen: [URL]
   - Verfügbare Funktionen identifizieren
   - Best Practices verstehen

2. [ ] Analysiere [vorhandene Code-Basis falls vorhanden]
   - Wiederverwendbare Funktionen finden
   - Patterns verstehen
   - Integration planen

3. [ ] Dokumentiere Analyse-Ergebnisse:
   - In README.md: Welche Funktionen werden genutzt
   - In Dependency-Matrix: Warum diese Libraries
```

**Warum wichtig:** Verhindert Neuentwicklung vorhandener Funktionalität

---

### Phase 2: Design-Entscheidungen dokumentieren

**Bei jeder wichtigen Entscheidung:**
1. **Library-Auswahl:** Eintrag in Dependency-Matrix
2. **Architektur-Pattern:** Begründung in Code-Kommentar oder ARCHITECTURE.md
3. **Abweichung von Spezifikation:** In CHANGELOG.md dokumentieren mit Begründung

**Format für Design-Entscheidung:**
```markdown
**Entscheidung:** [Was wurde entschieden]
**Alternativen betrachtet:** [Was wurde NICHT gewählt]
**Begründung:** [Warum diese Wahl]
**Trade-offs:** [Was gibt man auf]
```

---

### Phase 3: Implementierungs-Strategie

#### **Iterativer Ansatz (EMPFOHLEN):**
```
1. Setup & Konfiguration (INI, Logging, Basis-Struktur)
   ↓
2. Kern-Funktionalität implementieren (Funktion für Funktion)
   ↓ (nach jeder Funktion optional testen)
3. Error-Handling hinzufügen
   ↓
4. Edge-Cases behandeln
   ↓
5. Dokumentation aktualisieren
```

**Nicht:** Alles auf einmal implementieren!

---

#### **Error-Handling zuerst:**
```python
# 1. Happy Path implementieren
def function():
    return result

# 2. Dann Error-Cases hinzufügen
def function():
    try:
        # Happy Path
        return result
    except SpecificError as e:
        logger.error(f"Details: {e}")
        # Recovery oder Re-Raise
    except AnotherError as e:
        logger.error(f"Details: {e}")
        # Recovery oder Re-Raise
```

**Für jeden Error-Case:**
- Aussagekräftige Error-Message
- Log-Eintrag mit Context
- Recovery-Strategie oder Graceful Fail

---

#### **Logging-Strategie:**

**Zwei Arten von Ausgaben trennen:**

1. **User-facing Messages (print/stdout):**
   - Progress-Updates
   - Interaktive Prompts
   - Finale Zusammenfassungen
   - Sollten freundlich und prägnant sein

2. **Debug/Audit Logs (logger):**
   - Technische Details
   - Alle wichtigen Checkpoints
   - Error-Details mit Stacktraces
   - Für Troubleshooting

**Log-Levels verwenden:**
```python
logger.debug("Technische Details für Debugging")
logger.info("Wichtiger Checkpoint erreicht")
logger.warning("Potentielles Problem, aber fortsetzbar")
logger.error("Fehler aufgetreten, aber behandelt")
logger.critical("Kritischer Fehler, Abbruch nötig")
```

---

#### **Code-Qualität Standards:**

**Zwingend für jede Funktion:**
- [ ] Type Hints für alle Parameter und Returns
- [ ] Vollständiger Docstring (Args, Returns, Raises)
- [ ] Error-Handling für wahrscheinliche Fehler
- [ ] Logging an wichtigen Checkpoints

**Docstring-Format:**
```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """
    [Eine Zeile Beschreibung]
    
    [Optional: Längere Erklärung bei komplexen Funktionen]
    
    Args:
        param1 (Type1): [Beschreibung]
        param2 (Type2): [Beschreibung]
        
    Returns:
        ReturnType: [Was wird zurückgegeben]
        
    Raises:
        ErrorType1: [Wann wird dieser Fehler geworfen]
        ErrorType2: [Wann wird dieser Fehler geworfen]
        
    Example:
        >>> result = function_name(val1, val2)
        >>> print(result)
        expected_output
    """
```

---

### Phase 4: Testing & Validierung

**Test-First Mindset:**
```
Vor Implementierung überlegen:
- Wie teste ich diese Funktion?
- Was sind Erfolgs-Kriterien?
- Welche Edge-Cases gibt es?
```

**Während Implementierung:**
- Teste jede Funktion einzeln (wo möglich)
- Verifiziere gegen Test-Szenarien in Spezifikation
- Dokumentiere unerwartetes Verhalten sofort

**Nach Implementierung:**
- Alle Test-Szenarien durchlaufen
- Edge-Cases behandelt
- Error-Cases getestet

---

### Phase 5: Dokumentations-Update (ZWINGEND)

**Bei JEDER Code-Änderung:**

1. **README.md aktualisieren:**
   - Installation-Schritte (falls geändert)
   - Verwendete Libraries dokumentieren
   - Setup-Anleitung (falls neue Steps)
   - Troubleshooting erweitern (bei neuen Fehlern)

2. **CHANGELOG.md pflegen:**
   - Alle Änderungen kategorisieren (Added/Changed/Fixed/Removed)
   - Chronologisch (neueste oben)
   - Begründungen bei Breaking Changes

3. **Weitere Dokumentation:**
   - [Projekt-spezifische Dokumente]
   - Code-Kommentare bei komplexer Logik
   - API-Dokumentation (falls vorhanden)

---

### Phase 6: Abschluss-Validierung

**Vor "Fertig"-Meldung Checkliste durchgehen:**

Siehe [✅ Validierungs-Checkliste](#-validierungs-checkliste-für-claude-code) am Ende dieses Dokuments.

**Nicht als "fertig" melden bevor alle Checkpoints ✅ sind!**

---

## Architektur & Komponenten

### Datenfluss

```
[Zeichne hier ein ASCII-Diagramm des Datenflusses]

Beispiel:
Datenquelle (Excel/API/DB)
        ↓
Python Script (Verarbeitung)
        ↓
    Validierung
    Transformation
    Aggregation
        ↓
Ziel-System (API/DB/Datei)
```

### Komponenten-Übersicht

```
[Projektstruktur]

Beispiel:
project_name/
├── config/
│   └── config.ini.template
├── src/
│   ├── main_script.py          # [Beschreibung]
│   ├── helper_module.py        # [Beschreibung]
│   └── data_processing.py      # [Beschreibung]
├── tests/                      # [Optional]
├── logs/                       # [Automatisch erstellt]
└── data/                       # [Falls benötigt]
```

### Modul-Verantwortlichkeiten

**[modul_name.py]**
- Zweck: [Was macht dieses Modul]
- Hauptfunktionen: [Funktion1], [Funktion2]
- Abhängigkeiten: [Andere Module, externe Libraries]

---

## Bibliotheken-Entscheidungen

### Dependency-Matrix

| Bibliothek | Version | Zweck | Warum diese? | Alternative erwogen | Trade-offs |
|------------|---------|-------|--------------|---------------------|------------|
| **[lib_name]** | [version] | [Hauptzweck] | [Begründung: Warum die beste Wahl] | ❌ [andere_lib] ([Grund gegen diese]) | [Was man aufgibt mit dieser Wahl] |
| **[lib_name2]** | [version] | [Hauptzweck] | [Begründung] | ✅ [andere_lib] (wäre auch OK, aber...) | [Trade-offs] |

**Beispiel-Einträge:**
| Bibliothek | Version | Zweck | Warum diese? | Alternative | Trade-offs |
|------------|---------|-------|--------------|-------------|------------|
| **requests** | 2.31+ | HTTP-Calls | De-facto Standard, stabil, gut dokumentiert | ❌ urllib (zu low-level) | Größere Dependency |
| **pandas** | 2.2+ | Datenverarbeitung | Mächtig für Tabellen, gute Excel-Integration | ⚠️ openpyxl (leichtgewichtiger, aber weniger Features) | Heavy dependency (~100MB) |

---

### Installation & Requirements

**requirements.txt:**
```txt
# Core Dependencies
[library]==x.y.z     # [Kurze Begründung]
[library2]>=x.y      # [Kurze Begründung]

# Optional Dependencies (auskommentiert)
# [optional_lib]>=x.y  # [Wofür optional benötigt]
```

**requirements-dev.txt:** (für Entwicklung/Testing)
```txt
pytest>=7.4.0
black>=23.0.0
mypy>=1.0.0
```

---

## ⚠️ KRITISCHE IMPLEMENTIERUNGS-HINWEISE

### Template für kritische Hinweise:

Nutze diese Struktur für jeden Fallstrick:

```markdown
### [Nummer]. [Thema]: [Kurze Problem-Beschreibung]

**Problem:** [Was kann schiefgehen]

**NICHT so:**
```python
# ❌ FALSCH - [Warum falsch]
[fehlerhafter Code]
```

**SONDERN so:**
```python
# ✅ RICHTIG - [Warum richtig]
[korrekter Code]
```

**Fehler wenn falsch:** `[Konkrete Error-Message die erscheint]`

**Warum:** [Technische Erklärung]

**Verhindere durch:** [Präventiv-Maßnahme]
```

---

### [Projekt-spezifische kritische Hinweise hier einfügen]

**Beispiele für typische Kategorien:**

#### 1. Authentication & Authorization
[Library-spezifische Fallstricke bei OAuth, API-Keys, etc.]

#### 2. API-Calls & Externe Services
[Rate Limiting, Payload-Formate, Endpoints]

#### 3. Daten-Validierung & -Transformation
[Edge Cases, Type Conversions, Encodings]

#### 4. Konfiguration & Umgebung
[Path-Handling, Environment Variables, OS-Unterschiede]

#### 5. Error-Handling & Recovery
[Welche Fehler abfangen, wie recovern, wann abbrechen]

---

## Funktions-Spezifikationen

### Template für jede Funktion:

```markdown
### [N]. function_name(param1: Type, param2: Type) -> ReturnType

**Zweck:** [Eine Zeile - was macht die Funktion]

**Workflow:**
1. [Schritt 1 - was passiert]
2. [Schritt 2]
3. [Schritt 3]

**Implementierungs-Hinweise:**
- [Wichtiger Punkt 1]
- [Wichtiger Punkt 2]
- ⚠️ [Kritischer Punkt - Fallstrick]

**Code-Beispiel:**
```python
def function_name(param1: Type, param2: Type) -> ReturnType:
    """
    [Vollständiger Docstring mit Args/Returns/Raises]
    """
    # Schritt 1: [Beschreibung]
    [code für Schritt 1]
    
    # Schritt 2: [Beschreibung]
    try:
        [code für Schritt 2]
    except SpecificError as e:
        logger.error(f"Schritt 2 fehlgeschlagen: {e}")
        # [Recovery-Strategie]
    
    # Schritt 3: [Beschreibung]
    [code für Schritt 3]
    
    return result
```

**Error-Handling:**
```python
# Erwartete Fehler und wie behandeln
try:
    result = function_name(param1, param2)
except SpecificError as e:
    # [Was tun bei diesem Fehler]
except AnotherError as e:
    # [Was tun bei diesem Fehler]
```

**Verwendung:**
```python
# Typischer Aufruf
result = function_name(value1, value2)
```

**Argumente:**
- `param1` (Type): [Detaillierte Beschreibung, Constraints, Defaults]
- `param2` (Type): [Detaillierte Beschreibung]

**Returns:**
- `ReturnType`: [Was wird zurückgegeben, Format, möglich None]

**Raises:**
- `ErrorType1`: [Unter welcher Bedingung]
- `ErrorType2`: [Unter welcher Bedingung]

**Dependencies:**
- [Andere Funktionen die aufgerufen werden]
- [Externe Libraries die verwendet werden]
```

---

### [Projekt-spezifische Funktionen hier auflisten]

#### Empfohlene Gruppierung:
1. **Setup & Initialisierung**
   - setup_environment()
   - load_config()

2. **Daten-Beschaffung**
   - fetch_data()
   - parse_input()

3. **Verarbeitung & Transformation**
   - process_data()
   - validate_data()
   - transform_data()

4. **Output & Persistierung**
   - save_results()
   - upload_data()

5. **Hauptprogramm**
   - main()

---

## Test-Szenarien & Erwartete Ausgaben

### Template für Test-Szenario:

```markdown
### Szenario [N]: [Titel - z.B. "Erstmaliger Lauf ohne Konfiguration"]

**Beschreibung:** [Was wird getestet]

**Voraussetzungen:**
- [Setup-Bedingung 1]
- [Setup-Bedingung 2]

**Befehl:**
```bash
[exakter Befehl zum Ausführen]
```

**Erwartete Ausgabe (Console/Logs):**
```
[YYYY-MM-DD HH:MM:SS] INFO: [Erwartete Log-Zeile 1]
[YYYY-MM-DD HH:MM:SS] INFO: [Erwartete Log-Zeile 2]
➤ [User-facing Nachricht]
[YYYY-MM-DD HH:MM:SS] INFO: ✓ [Erfolgs-Meldung]
```

**Erwartetes Verhalten:**
- [ ] [Checkpoint 1 - was sollte passiert sein]
- [ ] [Checkpoint 2 - Dateien erstellt, API-Call erfolgreich, etc.]
- [ ] [Checkpoint 3]

**Erfolg wenn:**
- [Kriterium 1]
- [Kriterium 2]

**Fehler wenn:**
- [Fehlerbedingung 1]
- [Fehlerbedingung 2]

**Nachfolgende Aktionen:**
- [Was sollte als nächstes getestet werden]
```

---

### [Projekt-spezifische Test-Szenarien]

**Empfohlene Standard-Szenarien:**

#### Szenario 1: Erstmaliger Lauf
[Keine Config, keine Daten, alles neu]

#### Szenario 2: Regulärer Lauf
[Config vorhanden, normale Bedingungen]

#### Szenario 3: Keine neuen Daten
[Alles aktuell, nichts zu tun]

#### Szenario 4: Fehlerhafte Eingabe
[Ungültige Config, fehlerhafte Daten]

#### Szenario 5: Externe Service nicht erreichbar
[Netzwerkfehler, API down]

#### Szenario 6: Authentifizierung fehlgeschlagen
[Credentials ungültig, Token abgelaufen]

---

## Häufige Fehler & Lösungen

### Template für Fehler-Dokumentation:

```markdown
### Error: "[Exakte Error-Message oder Pattern]"

**Symptom:** [Was sieht der Benutzer]

**Ursache:** [Was ist technisch falsch]

**Lösung:**
```bash
# Schritt-für-Schritt Befehle
[Befehl 1]
[Befehl 2]
```

**Oder (falls mehrere Lösungen):**
- **Option A:** [Schnelle Lösung]
- **Option B:** [Umfassende Lösung]

**Verhindern:** [Wie kann man diesen Fehler zukünftig vermeiden]

**Verwandte Fehler:** [Ähnliche Probleme die gleichen Ursprung haben]
```

---

### [Projekt-spezifische Fehler hier einfügen]

**Typische Kategorien:**

#### Installation & Setup
[Dependency-Fehler, Konfiguration fehlt]

#### Authentifizierung
[Credentials ungültig, Token-Probleme]

#### Daten-Verarbeitung
[Validierung fehlgeschlagen, Format-Fehler]

#### Externe Services
[API-Fehler, Netzwerk-Probleme]

#### File System
[Permissions, Pfade, Encoding]

---

## Konfiguration

### INI-Datei Struktur

**Template: config.ini.template**
```ini
# [Projektname] - Konfigurationsvorlage
# ================================================
# ANLEITUNG:
# 1. Kopiere diese Datei nach: config/[name].ini
# 2. Passe die Werte an deine Umgebung an
# 3. Diese INI ist in .gitignore (nicht committen!)
# ================================================

[Section1]
# [Beschreibung dieser Section]
parameter1 = default_value     # [Erklärung was dieser Parameter macht]
parameter2 = /path/to/file     # [Format-Hinweise, z.B. "Absoluter Pfad"]

[Section2]
# [Beschreibung]
api_key = YOUR_API_KEY_HERE    # [Wo bekommt man das?]
endpoint = https://api.example.com

[Options]
dry_run = true                 # [true = Testmodus, false = Produktiv]
log_level = INFO               # [DEBUG|INFO|WARNING|ERROR|CRITICAL]
```

---

### Konfiguration Validierung

**Im Code prüfen:**
```python
def load_config() -> ConfigParser:
    """Lädt und validiert Konfiguration"""
    config = ConfigParser('config/config.ini')
    
    # Pflicht-Parameter prüfen
    required_params = [
        ('Section1', 'parameter1'),
        ('Section2', 'api_key'),
    ]
    
    for section, param in required_params:
        if not config.get(section, param):
            raise ValueError(f"Pflicht-Parameter fehlt: [{section}] {param}")
    
    # Validierung von Werten
    if config.getint('Options', 'timeout') < 1:
        raise ValueError("Timeout muss >= 1 sein")
    
    return config
```

---

## Logging-Strategie

### Log-File Format

**Dateiname:**
```
logs/[scriptname]_YYYYMMDD_HHMMSS.log
```

**Log-Einträge:**
```
[YYYY-MM-DD HH:MM:SS] LEVEL: Modul.Funktion - Nachricht
```

**Beispiel:**
```
[2026-01-07 10:15:23] INFO: main.authenticate - Starte Authentifizierung
[2026-01-07 10:15:24] DEBUG: auth.load_token - Token aus Datei geladen
[2026-01-07 10:15:25] ERROR: api.call - Request fehlgeschlagen: 500
```

---

### Log-Level Verwendung

| Level | Wann verwenden | Beispiel |
|-------|----------------|----------|
| DEBUG | Technische Details für Debugging | "Variablen-Wert: x=123" |
| INFO | Wichtige Checkpoints, normale Abläufe | "Daten erfolgreich verarbeitet" |
| WARNING | Potentielle Probleme, aber fortsetzbar | "Deprecated Funktion verwendet" |
| ERROR | Fehler aufgetreten, aber behandelt | "API-Call fehlgeschlagen, Retry..." |
| CRITICAL | Kritischer Fehler, Programmabbruch | "Konfiguration fehlt, kann nicht starten" |

---

## ✅ Validierungs-Checkliste für Claude Code

### Vor Abschluss der Implementierung diese Liste durchgehen:

#### **Code-Qualität**
- [ ] Alle Funktionen haben Type Hints
- [ ] Alle Funktionen haben vollständige Docstrings (Args/Returns/Raises/Example)
- [ ] UTF-8 Encoding durchgängig (falls relevant)
- [ ] [Projekt-spezifische Code-Konvention] eingehalten
- [ ] Keine TODO/FIXME im finalen Code
- [ ] Code ist kommentiert wo nötig (komplexe Logik)

#### **Funktionalität**
- [ ] Alle Funktionen aus Spezifikation implementiert
- [ ] Alle Test-Szenarien durchlaufen erfolgreich
- [ ] Error-Handling für alle wahrscheinlichen Fehler implementiert
- [ ] Edge-Cases behandelt (leere Eingabe, None, etc.)
- [ ] Logging an allen wichtigen Checkpoints
- [ ] Dry-Run-Modus funktioniert (falls spezifiziert)

#### **Externe Integration**
- [ ] [Externe Library X] wurde analysiert
- [ ] Wiederverwendbare Funktionen identifiziert und genutzt
- [ ] API-Calls funktionieren (falls zutreffend)
- [ ] Authentifizierung funktioniert (falls zutreffend)
- [ ] Token-Refresh implementiert (falls zutreffend)

#### **Konfiguration**
- [ ] Konfiguration vollständig in INI/Config-File
- [ ] config.ini.template erstellt mit Kommentaren
- [ ] Pflicht-Parameter werden validiert
- [ ] Sensible Daten NICHT in Config (Keyring/Env-Vars)
- [ ] .gitignore enthält config.ini (nicht config.ini.template)

#### **Dokumentation**
- [ ] README.md vollständig aktualisiert:
  - Installation-Schritte
  - Setup-Anleitung
  - Verwendete Libraries dokumentiert
  - Verwendung/Usage-Beispiele
  - Troubleshooting-Section
- [ ] CHANGELOG.md aktualisiert:
  - Alle Änderungen kategorisiert (Added/Changed/Fixed/Removed)
  - Begründungen bei Breaking Changes
  - Version und Datum korrekt
- [ ] [Weitere projekt-spezifische Dokumentation] aktualisiert
- [ ] Dependency-Matrix ausgefüllt (warum welche Library)

#### **Projekt-Struktur**
- [ ] Alle Dateien im richtigen Ordner (src/, config/, logs/, etc.)
- [ ] .gitignore vollständig (logs/, *.ini außer template, tokens/, etc.)
- [ ] requirements.txt vollständig
- [ ] requirements-dev.txt vorhanden (falls Tests)
- [ ] README.md, CHANGELOG.md, TODO.md existieren

#### **Testing & Validierung**
- [ ] Mindestens ein vollständiger End-to-End-Test durchgeführt
- [ ] Alle Test-Szenarien aus Spezifikation getestet
- [ ] Error-Cases getestet (ungültige Eingabe, etc.)
- [ ] Logging-Output überprüft (keine Exceptions in Logs)
- [ ] Performance akzeptabel (falls relevant)

#### **Sicherheit & Best Practices**
- [ ] Keine Credentials im Code
- [ ] Keine Credentials in Logs
- [ ] Sensible Daten in Keyring/Secrets-Manager
- [ ] Input-Validierung implementiert
- [ ] SQL-Injection-sicher (falls DB-Zugriff)
- [ ] XSS-sicher (falls Web-Output)

#### **Deployment-Bereitschaft**
- [ ] Kann auf Zielsystem ausgeführt werden
- [ ] Alle Dependencies installierbar
- [ ] Setup-Prozess dokumentiert und getestet
- [ ] Task Scheduler / Cron-Job konfigurierbar (falls zutreffend)

---

### ⚠️ Wichtig: Nicht als "fertig" melden bevor alle relevanten Checkpoints ✅ sind!

---

## Migration & Versioning

### Template für Migrations-Guide

**Nutze diese Struktur wenn Breaking Changes eingeführt werden:**

```markdown
## Migration von v[X.Y] zu v[A.B]

### Übersicht der Änderungen
- [Änderung 1 - High-Level]
- [Änderung 2]

### Breaking Changes

#### Change 1: [Titel der Änderung]

**v[X.Y] (alt):**
```python
[alter Code oder Konfiguration]
```

**v[A.B] (neu):**
```python
[neuer Code oder Konfiguration]
```

**Grund für Änderung:** [Warum war das nötig]

**Auswirkung:** 
- [Was passiert mit bestehenden Daten/Instanzen]
- [Was funktioniert nicht mehr]

**Action Required:**
```bash
# Schritt-für-Schritt was Benutzer tun muss
[Befehl 1]
[Befehl 2]
```

**Fallback (falls nötig):**
```bash
# Wie man zur alten Version zurückkehrt
git checkout v[X.Y]
[weitere Schritte]
```

---

#### Change 2: [Nächste Änderung]
[Gleiche Struktur]
```

---

### Semantic Versioning

**Version-Schema: MAJOR.MINOR.PATCH**

- **MAJOR:** Breaking Changes (z.B. 1.0 → 2.0)
- **MINOR:** Neue Features, abwärtskompatibel (z.B. 1.0 → 1.1)
- **PATCH:** Bugfixes, abwärtskompatibel (z.B. 1.0.0 → 1.0.1)

**Beispiele:**
- `v1.0.0` → `v1.0.1`: Bugfix, kein Breaking Change
- `v1.0.0` → `v1.1.0`: Neues Feature, alte Funktionalität weiter nutzbar
- `v1.0.0` → `v2.0.0`: Breaking Change, Migration erforderlich

---

## Anhang

### Nützliche Links
- [Projekt Repository]: [URL]
- [Externe API Dokumentation]: [URL]
- [Library Dokumentation]: [URL]
- [Issue Tracker]: [URL]

### Glossar
- **[Term 1]**: [Definition]
- **[Term 2]**: [Definition]

### Kontakt & Support
- **Autor:** [Name]
- **Email:** [Email]
- **GitHub:** [URL]

---

## Versions-Historie dieser Spezifikation

- **v1.0.0** - YYYY-MM-DD: Initiale Spezifikation erstellt
- **v1.1.0** - YYYY-MM-DD: [Änderungen an Spezifikation]

---

**Spezifikation erstellt:** [Datum]  
**Zuletzt aktualisiert:** [Datum]  
**Version:** [Version]
