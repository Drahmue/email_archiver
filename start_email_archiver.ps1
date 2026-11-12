# email_archiver - Start-Skript fuer den HauServer
# Wird alle 15 Minuten per Task Scheduler ausgefuehrt (Task \AHSkripts\email_archiver, Konto Administrator,
# weil das IMAP-Passwort im Schluesselbund des Administrators liegt).
# Fehler meldet der Task-Watchdog (haeufig laufender Task, keine eigene Telegram-Meldung).
#
# Aufruf: start_email_archiver.ps1 [-DryRun]

param([switch]$DryRun)

$ProjectDir = "D:\Dataserver\_Batchprozesse\email_archiver"
$VenvPython = "$ProjectDir\.venv\Scripts\python.exe"
$Script     = "$ProjectDir\src\main.py"
$LogFile    = "$ProjectDir\logs\email_archiver_$(Get-Date -Format 'yyyy-MM').log"

Set-Location -Path $ProjectDir
New-Item -ItemType Directory -Force -Path "$ProjectDir\logs" | Out-Null

function Write-Log([string]$Text) {
    Add-Content -Path $LogFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - START - $Text" -Encoding UTF8
}

if (-not (Test-Path $VenvPython)) {
    Write-Log "FEHLER: Python-Interpreter nicht gefunden: $VenvPython"
    exit 1
}

# Code aktualisieren; ein Fehler hier bricht den Lauf nicht ab (laeuft mit dem vorhandenen Stand)
$git = & git -C $ProjectDir pull --ff-only 2>&1
if ($LASTEXITCODE -ne 0) { Write-Log "WARNUNG: git pull fehlgeschlagen: $($git -join ' | ')" }
elseif ("$git" -notmatch 'Already up to date') { Write-Log "git pull: $($git -join ' | ')" }

# Chromium liegt im Projektordner (unabhaengig vom Benutzerprofil des Tasks)
$env:PLAYWRIGHT_BROWSERS_PATH = "$ProjectDir\ms-playwright"

$pyArgs = @($Script); if ($DryRun) { $pyArgs += '--dry-run' }
# Bei Exit <> 0 haengt Invoke-Logged die Konsolenausgabe (z. B. Traceback) ans Log an (datahub DH-063).
$lib = "D:\Dataserver\_Batchprozesse\_shared\Invoke-Logged.psm1"
if (Test-Path $lib) {
    Import-Module $lib -Force
    exit (Invoke-Logged -FilePath $VenvPython -ArgumentList $pyArgs -Mode OnError -LogFile $LogFile)
}
& $VenvPython @pyArgs
exit $LASTEXITCODE
