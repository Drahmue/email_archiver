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
$gitRC = $LASTEXITCODE
if ($gitRC -ne 0) { Write-Log "WARNUNG: git pull fehlgeschlagen: $($git -join ' | ')" }
elseif ("$git" -notmatch 'Already up to date') { Write-Log "git pull: $($git -join ' | ')" }

# Anhaltende Pull-Fehler melden (datahub DH-062): einzelne Aussetzer (z. B. 06.11.2026 "Empty reply") still,
# ab $PullWarnAb Fehlern hintereinander (~2 h bei 15-Min.-Takt) Telegram-Warnung, hoechstens einmal je Tag
$PullWarnAb = 8
$PullState  = "$ProjectDir\logs\git_pull_status.json"
try {
    $st = if (Test-Path $PullState) { Get-Content $PullState -Raw | ConvertFrom-Json } else { $null }
    if (-not $st) { $st = [pscustomobject]@{ fehler_folge = 0; fehler_seit = ''; gemeldet_am = '' } }
    if ($gitRC -eq 0) {
        if ($st.fehler_folge -ge $PullWarnAb) { Write-Log "git pull wieder erfolgreich nach $($st.fehler_folge) Fehlern" }
        $st.fehler_folge = 0; $st.fehler_seit = ''
    } else {
        if ($st.fehler_folge -eq 0) { $st.fehler_seit = (Get-Date -Format 'yyyy-MM-dd HH:mm') }
        $st.fehler_folge = [int]$st.fehler_folge + 1
        $heute = Get-Date -Format 'yyyy-MM-dd'
        if ($st.fehler_folge -ge $PullWarnAb -and $st.gemeldet_am -ne $heute) {
            $notifyLib = "D:\Dataserver\_Batchprozesse\_shared\Notify-Telegram.psm1"
            if (Test-Path $notifyLib) {
                Import-Module $notifyLib -Force
                Send-WarningNotification -ScriptName "email_archiver" `
                    -Text "git pull scheitert seit $($st.fehler_seit) ($($st.fehler_folge) Laeufe), laeuft mit altem Code. $(($git | Select-Object -First 1))"
                $st.gemeldet_am = $heute
                Write-Log "WARNUNG per Telegram gemeldet: git pull $($st.fehler_folge)x hintereinander fehlgeschlagen"
            }
        }
    }
    $st | ConvertTo-Json | Set-Content -Path $PullState -Encoding ASCII
} catch { Write-Log "WARNUNG: git_pull_status.json nicht verarbeitbar: $($_.Exception.Message)" }

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
