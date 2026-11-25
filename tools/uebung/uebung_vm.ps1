# kaiscribe-uebung-n1 (25.11.2026): Übungsdienst auf der Automaten-VM einrichten/prüfen/abbauen – als rakadmin (vmssh.py).
#   -Schritt lage | einrichten | start | beleg | aus
# Dateien vorher nach C:\RaK\einrichtung\uebung\ : paket.zip (prog\ + web\), optional konten.json (nur Hashes).
# Dienst: geplante Aufgabe \RaK\RaK KaiScribe Uebung (rakauto, nur wenn angemeldet; bei Anmeldung + alle 5 min, eine Instanz)
# → py -3.12 uebung_dienst.py auf 127.0.0.1:18555; tailscale serve --https=8555 → nur im Tailnet (Georg: nur dieser Port).
# Nichts an CAS, Plaza, Brücke, Roboter. Ausgabe nur Zustände/Zähler.
param([Parameter(Mandatory = $true)][ValidateSet('lage', 'einrichten', 'start', 'beleg', 'aus')][string]$Schritt)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$B = 'C:\RaK\kaiscribe_uebung'
$Z = 'C:\RaK\einrichtung\uebung'
$TS = 'C:\Program Files\Tailscale\tailscale.exe'
$PORT_TN = 8555
$PORT_LOKAL = 18555
$AUFGABE = 'RaK KaiScribe Uebung'
$AEND = 'C:\RaK\einrichtung\aenderungen.log'
function Dienst() { @(Get-CimInstance Win32_Process -Filter "Name like 'py%'" | Where-Object { [string]$_.CommandLine -match 'kaiscribe_uebung\\prog\\uebung_dienst\.py' }) }
function Lauscht($p) { @(Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) }
function Status() {
  try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 ("http://127.0.0.1:{0}/api/status" -f $PORT_LOKAL); return $r.Content } catch { return 'keine Antwort' }
}
function Serve() { try { (& $TS serve status 2>&1 | Out-String).Trim() -replace '\s+', ' ' } catch { 'serve nicht lesbar' } }
'JETZT=' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss ddd') + ' ' + $env:USERNAME

if ($Schritt -eq 'lage') {
  'PORT{0}_LAUSCHT={1} PORT{2}_LAUSCHT={3}' -f $PORT_TN, (Lauscht $PORT_TN).Count, $PORT_LOKAL, (Lauscht $PORT_LOKAL).Count
  'TAILSCALE=' + (Test-Path $TS) + ' SERVE=' + (Serve)
  'LAUFWERKE_CMD=' + (Test-Path 'C:\RaK\laufwerke.cmd')
  if (Test-Path 'C:\RaK\laufwerke.cmd') { Get-Content 'C:\RaK\laufwerke.cmd' | Where-Object { $_ -notmatch 'net use|/user:|pass|pwd' } | Select-Object -First 12 | ForEach-Object { 'LW ' + $_ } }
  'PY312=' + [bool](& C:\Windows\py.exe -3.12 -c "print(1)" 2>$null)
  'QUSER=' + ((quser 2>$null | Out-String).Trim() -replace '\s+', ' ')
  $t = Get-ScheduledTask -TaskPath '\RaK\' -TaskName $AUFGABE -ErrorAction SilentlyContinue
  'AUFGABE=' + $(if ($t) { $t.State } else { 'fehlt' }) + ' DIENST_PROZESSE=' + (Dienst).Count
  'KASDB=' + (Test-Path 'C:\RaK\kaiscribe_lernen\prog\bruecke\casdb.py') + ' SENF_ABLAGE=' + (Test-Path 'C:\RaK\opus_senf\senf')
  'BASIS=' + (Test-Path $B) + ' TAGE=' + @(Get-ChildItem (Join-Path $B 'daten') -Directory -ErrorAction SilentlyContinue).Count
  $dbd = Get-ScheduledTask -TaskPath '\RaK\' -TaskName 'RaK DB-Dienst' -ErrorAction SilentlyContinue
  if ($dbd) { 'MUSTER_DBDIENST principal=' + $dbd.Principal.UserId + ' logon=' + $dbd.Principal.LogonType }
  exit 0
}

if ($Schritt -eq 'einrichten') {
  if (-not (Test-Path (Join-Path $Z 'paket.zip'))) { 'ROT paket.zip fehlt'; exit 2 }
  if ((Lauscht $PORT_TN).Count -and -not ((Serve) -match "$PORT_TN")) { 'ROT Port ' + $PORT_TN + ' schon belegt (fremd)'; exit 3 }
  foreach ($d in @($B, "$B\prog", "$B\web", "$B\daten")) { New-Item -ItemType Directory -Force $d | Out-Null }
  $neu = Join-Path $B 'neu'
  if (Test-Path $neu) { Remove-Item -Recurse -Force $neu }
  Expand-Archive -LiteralPath (Join-Path $Z 'paket.zip') -DestinationPath $neu -Force
  foreach ($teil in 'prog', 'web') {
    robocopy (Join-Path $neu $teil) (Join-Path $B $teil) /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
    'KOPIE {0} dateien={1}' -f $teil, @(Get-ChildItem -Recurse -File (Join-Path $B $teil)).Count
  }
  Remove-Item -Recurse -Force $neu
  icacls $B /grant 'rakauto:(OI)(CI)M' /T /C /Q | Out-Null
  $k = Join-Path $Z 'konten.json'
  if (Test-Path $k) {
    Move-Item -Force $k (Join-Path $B 'konten.json')
    icacls (Join-Path $B 'konten.json') /inheritance:r /grant:r 'rakauto:R' '*S-1-5-32-544:F' '*S-1-5-18:F' /Q | Out-Null
    'KONTEN neu (nur Hashes)'
  }
  'KONTEN=' + (Test-Path (Join-Path $B 'konten.json'))
  $arg = '/c C:\RaK\laufwerke.cmd C:\Windows\py.exe -3.12 -X utf8 {0}\prog\uebung_dienst.py --basis {0} --port {1}' -f $B, $PORT_LOKAL
  $a = New-ScheduledTaskAction -Execute 'C:\Windows\System32\cmd.exe' -Argument $arg -WorkingDirectory "$B\prog"
  $t1 = New-ScheduledTaskTrigger -AtLogOn -User 'rakauto'
  $t2 = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
  $p = New-ScheduledTaskPrincipal -UserId 'rakauto' -LogonType Interactive -RunLevel Limited
  $s = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
  Register-ScheduledTask -TaskPath '\RaK\' -TaskName $AUFGABE -Action $a -Trigger @($t1, $t2) -Principal $p -Settings $s -Force | Out-Null
  Add-Content $AEND ('{0:yyyy-MM-dd HH:mm:ss} kaiscribe-uebung-n1 Aufgabe {1} eingerichtet (127.0.0.1:{2}, serve {3})' -f (Get-Date), $AUFGABE, $PORT_LOKAL, $PORT_TN)
  'AUFGABE eingerichtet'
  $Schritt = 'start'
}

if ($Schritt -eq 'start') {
  foreach ($x in (Dienst)) { Stop-Process -Id $x.ProcessId -Force -ErrorAction SilentlyContinue }
  Start-Sleep 2
  Enable-ScheduledTask -TaskPath '\RaK\' -TaskName $AUFGABE | Out-Null
  Start-ScheduledTask -TaskPath '\RaK\' -TaskName $AUFGABE
  $ende = (Get-Date).AddSeconds(60)
  do { Start-Sleep 3 } while (-not (Lauscht $PORT_LOKAL).Count -and (Get-Date) -lt $ende)
  'LOKAL_LAUSCHT=' + (Lauscht $PORT_LOKAL).Count + ' DIENST_PROZESSE=' + (Dienst).Count
  $o = (& $TS serve --bg ("--https={0}" -f $PORT_TN) ("http://127.0.0.1:{0}" -f $PORT_LOKAL) 2>&1 | Out-String).Trim()
  'SERVE_SETZEN ' + ($o -replace '\s+', ' ')
  $Schritt = 'beleg'
}

if ($Schritt -eq 'beleg') {
  $t = Get-ScheduledTask -TaskPath '\RaK\' -TaskName $AUFGABE -ErrorAction SilentlyContinue
  $i = if ($t) { Get-ScheduledTaskInfo -TaskPath '\RaK\' -TaskName $AUFGABE } else { $null }
  'AUFGABE=' + $(if ($t) { "$($t.State) letzter=$($i.LastRunTime.ToString('HH:mm:ss')) ergebnis=$($i.LastTaskResult)" } else { 'fehlt' })
  'DIENST_PROZESSE=' + (Dienst).Count + ' LOKAL_LAUSCHT=' + (Lauscht $PORT_LOKAL).Count
  'STATUS ' + (Status)
  'SERVE ' + (Serve)
  'TAGE ' + ((@(Get-ChildItem (Join-Path $B 'daten') -Directory -ErrorAction SilentlyContinue) | ForEach-Object { $_.Name }) -join ',')
  'KONTEN=' + (Test-Path (Join-Path $B 'konten.json')) + ' WEB_INDEX=' + (Test-Path (Join-Path $B 'web\index.html'))
  exit 0
}

if ($Schritt -eq 'aus') {
  $o = (& $TS serve ("--https={0}" -f $PORT_TN) off 2>&1 | Out-String).Trim()
  'SERVE_AUS ' + ($o -replace '\s+', ' ')
  Disable-ScheduledTask -TaskPath '\RaK\' -TaskName $AUFGABE -ErrorAction SilentlyContinue | Out-Null
  Stop-ScheduledTask -TaskPath '\RaK\' -TaskName $AUFGABE -ErrorAction SilentlyContinue
  foreach ($x in (Dienst)) { Stop-Process -Id $x.ProcessId -Force -ErrorAction SilentlyContinue }
  Add-Content $AEND ('{0:yyyy-MM-dd HH:mm:ss} kaiscribe-uebung-n1 Aufgabe {1} aus, serve {2} off' -f (Get-Date), $AUFGABE, $PORT_TN)
  'AUS DIENST_PROZESSE=' + (Dienst).Count + ' SERVE=' + (Serve)
}
