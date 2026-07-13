# run_archiver.ps1 — Starter für email_archiver
# Aktiviert das .venv und startet src/main.py aus dem Projektverzeichnis.

$ProjectRoot = $PSScriptRoot
$Python      = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Script      = Join-Path $ProjectRoot "src\main.py"

if (-not (Test-Path $Python)) {
    Write-Error "Python-Interpreter nicht gefunden: $Python"
    exit 1
}

& $Python $Script @args
exit $LASTEXITCODE
