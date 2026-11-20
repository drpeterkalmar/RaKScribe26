$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$u = [Console]::In.ReadLine(); $p = [Console]::In.ReadLine()
$neu = $false
if (-not (Test-Path X:\)) { $c = New-Object System.Management.Automation.PSCredential($u, (ConvertTo-SecureString $p -AsPlainText -Force)); New-PSDrive -Name X -PSProvider FileSystem -Root '\\casmed\casmed$' -Credential $c -Persist -Scope Global | Out-Null; $c = $null; $neu = $true }
$p = $null
"x_verbunden=" + (Test-Path X:\RaKScribe)
try { & C:\Windows\py.exe -3.12 -X utf8 $env:KF_SKRIPT @($env:KF_ARGS -split " ") 2>&1 | ForEach-Object { "$_" } }
finally { if ($neu) { Remove-PSDrive -Name X -Force -EA SilentlyContinue; net use X: /delete /y 2>&1 | Out-Null } ; "x_getrennt=" + (-not (Test-Path X:\)) }
