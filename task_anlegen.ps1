# Legt den Task \AHSkripts\email_archiver an (alle 15 Minuten, Konto Administrator, unabhaengig von der Anmeldung).
# Administrator statt SYSTEM, weil das IMAP-Passwort im Schluesselbund des Administrators liegt.
# Fragt einmal das Kennwort des Administrators ab (wird nur von Windows fuer den Task gespeichert).
# Read-Host statt Get-Credential (Get-Credential lieferte in AHs Konsole nichts zurueck, morgenbrief 2026-10-24).

$Dir    = "D:\Dataserver\_Batchprozesse\email_archiver"
$User   = "$env:COMPUTERNAME\Administrator"
$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$Dir\start_email_archiver.ps1`"" `
    -WorkingDirectory $Dir

# Start zur naechsten Viertelstunde, dann alle 15 Minuten ohne Ende
$Jetzt = Get-Date
$Start = $Jetzt.Date.AddHours($Jetzt.Hour).AddMinutes([math]::Ceiling(($Jetzt.Minute + 1) / 15) * 15)
$Trigger = New-ScheduledTaskTrigger -Once -At $Start -RepetitionInterval (New-TimeSpan -Minutes 15)
# Ortszeit ohne Zeitzonen-Offset (standards_automation.md Abschnitt 3)
$Trigger.StartBoundary = $Start.ToString("yyyy-MM-ddTHH:mm:ss")

$Settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -MultipleInstances IgnoreNew -StartWhenAvailable

$Pass  = Read-Host -AsSecureString "Kennwort fuer $User"
$Plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($Pass))
Register-ScheduledTask -TaskPath "\AHSkripts\" -TaskName "email_archiver" -Action $Action -Trigger $Trigger `
    -Settings $Settings -User $User -Password $Plain -RunLevel Highest `
    -Description "datahub DH-044: IMAP '01 fuer Ablage' -> Sammelordner\Korrespondenz, '01 fuer Belege' -> _datahub\belege\eingang" | Out-Null
$Plain = $null

Write-Host "Task angelegt:"
$t = Get-ScheduledTask -TaskPath "\AHSkripts\" -TaskName "email_archiver"
$t | Format-List TaskName, State
Write-Host "StartBoundary: $($t.Triggers[0].StartBoundary)  Intervall: $($t.Triggers[0].Repetition.Interval)"
