<#
sm_probe.ps1 1.0 - Abnahme senf-ibl-speechmagic-paste-n1 (21.11.2026) am Buero-PC, PS 5.1, ASCII. Nur Testpatient 451898.
  -Modus lesen   : offenes SpeechMagic-Diktatfenster "CASOnline Diktat ... User: <kz>" -> Text des RichEdit (woertlich, nur
                   synthetische Testtexte), Markierung (EM_GETSEL), Zeilen mit "[SENF", Knopfliste. Aendert nichts.
  -Modus fertig  : nur wenn der Text "-Marke" enthaelt (Testsenf): Knopf "Fertig stellen" (BM_CLICK), warten bis zu,
                   danach KaiScribe-Warnfenster ("SENF-Zeile noch im Diktat") suchen, Text melden und schliessen (WM_CLOSE).
  -Modus mikro   : Windows-Mikrofonanzeige (HKCU ...\CapabilityAccessManager\ConsentStore\microphone, auch NonPackaged):
                   je App LastUsedTimeStart/Stop, "in Benutzung" ja/nein. Aendert nichts.
  -Modus warnung : nur KaiScribe-Warnfenster suchen (Text), nicht schliessen.
Ausgabe: JSON (eine Zeile, ASCII-maskiert) + -Aus (UTF-8). Exit 0 = ok.
#>
param(
    [ValidateSet('lesen', 'fertig', 'mikro', 'warnung')][string]$Modus = 'lesen',
    [string]$Kuerzel = 'kp',
    [string]$Marke = 'TESTSENF',
    [string]$Aus = '',
    [int]$WarteS = 30
)
$ErrorActionPreference = 'Stop'
$erg = [ordered]@{ version = '1.0'; modus = $Modus; status = 'fehler'; grund = '' }
function Ende([string]$s, [string]$g) {
    $erg.status = $s; $erg.grund = $g
    $j = $erg | ConvertTo-Json -Depth 6 -Compress
    if ($Aus) { [IO.File]::WriteAllText($Aus, $j, (New-Object Text.UTF8Encoding($false))) }
    Write-Output ($j -replace '[^\x00-\x7F]', '?')
    if ($s -eq 'ok') { exit 0 } else { exit 2 }
}
if (-not ('SmProbe.W' -as [type])) {
    Add-Type -TypeDefinition @'
using System; using System.Collections.Generic; using System.Runtime.InteropServices; using System.Text;
namespace SmProbe {
public static class W {
  delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc f, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr p, EnumProc f, IntPtr l);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool IsWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder sb, int n);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern IntPtr SendMessageTimeout(IntPtr h, uint m, IntPtr w, StringBuilder l, uint f, uint t, out IntPtr r);
  [DllImport("user32.dll")] static extern IntPtr SendMessageTimeout(IntPtr h, uint m, IntPtr w, IntPtr l, uint f, uint t, out IntPtr r);
  public static IntPtr[] Alle() { List<IntPtr> l = new List<IntPtr>(); EnumWindows(delegate(IntPtr h, IntPtr x) { if (IsWindowVisible(h)) l.Add(h); return true; }, IntPtr.Zero); return l.ToArray(); }
  public static uint Pid(IntPtr h) { uint p; GetWindowThreadProcessId(h, out p); return p; }
  public static IntPtr[] Kinder(IntPtr p) { List<IntPtr> l = new List<IntPtr>(); EnumChildWindows(p, delegate(IntPtr h, IntPtr x) { l.Add(h); return true; }, IntPtr.Zero); return l.ToArray(); }
  public static string Klasse(IntPtr h) { StringBuilder sb = new StringBuilder(256); GetClassName(h, sb, 256); return sb.ToString(); }
  public static string Text(IntPtr h) { IntPtr r; if (SendMessageTimeout(h, 0x000E, IntPtr.Zero, IntPtr.Zero, 2, 2000, out r) == IntPtr.Zero) return null; int n = (int)r;
      StringBuilder sb = new StringBuilder(n + 2); if (SendMessageTimeout(h, 0x000D, (IntPtr)(n + 1), sb, 2, 2000, out r) == IntPtr.Zero) return null; return sb.ToString(); }
  public static long Sel(IntPtr h) { IntPtr r; if (SendMessageTimeout(h, 0x00B0, IntPtr.Zero, IntPtr.Zero, 2, 2000, out r) == IntPtr.Zero) return -2; return (long)r; }
  public static int Hoehe(IntPtr h) { RECT r; if (!GetWindowRect(h, out r)) return 0; return r.B - r.T; }
  public static bool Klick(IntPtr h) { return PostMessage(h, 0x00F5, IntPtr.Zero, IntPtr.Zero); }
  public static bool Zu(IntPtr h) { return PostMessage(h, 0x0010, IntPtr.Zero, IntPtr.Zero); }
}}
'@
}
function Falt([string]$t) { if ($null -eq $t) { return '' }; return ((($t.Replace('&', '')) -replace '\s+', ' ').Trim()).ToLowerInvariant() }
function Get-Diktat {
    $pids = @(Get-Process CASSpeechMagic -ErrorAction SilentlyContinue | ForEach-Object { [uint32]$_.Id })
    foreach ($h in [SmProbe.W]::Alle()) {
        if ($pids -notcontains [SmProbe.W]::Pid($h)) { continue }
        $t = Falt ([SmProbe.W]::Text($h))
        if ($t -like 'casonline diktat*' -and $t.EndsWith('user: ' + $Kuerzel.ToLowerInvariant())) { return $h }
    }
    return [IntPtr]::Zero
}
function Get-Feld([IntPtr]$h) {
    $re = @([SmProbe.W]::Kinder($h) | Where-Object { [SmProbe.W]::IsWindowVisible($_) -and ([SmProbe.W]::Klasse($_) -match 'RichEdit') -and ([SmProbe.W]::Hoehe($_) -gt 100) } |
        Sort-Object { [SmProbe.W]::Hoehe($_) } -Descending)
    if ($re.Count -gt 0) { return $re[0] } else { return [IntPtr]::Zero }
}
function Get-Warnung {
    $o = @()
    $ks = @(Get-Process | Where-Object { $_.ProcessName -match '^(KaiScribe|rakscribe26)$' } | ForEach-Object { [uint32]$_.Id })
    foreach ($h in [SmProbe.W]::Alle()) {
        if ($ks -notcontains [SmProbe.W]::Pid($h)) { continue }
        $t = [string][SmProbe.W]::Text($h)
        if ($t -match 'SENF-Zeile noch im Diktat') {
            $texte = @([SmProbe.W]::Kinder($h) | ForEach-Object { [string][SmProbe.W]::Text($_) } | Where-Object { $_ })
            $o += @{ h = $h; titel = $t; texte = $texte }
        }
    }
    return $o
}
function Lies([IntPtr]$h) {
    $f = Get-Feld $h
    if ($f -eq [IntPtr]::Zero) { return $null }
    $txt = [string][SmProbe.W]::Text($f)
    $sel = [SmProbe.W]::Sel($f)
    return [ordered]@{ klasse = [SmProbe.W]::Klasse($f); text = $txt; laenge = $txt.Length
        sel_anfang = ($sel -band 0xFFFF); sel_ende = (($sel -shr 16) -band 0xFFFF)
        senf_zeilen = @($txt -split "`r`n|`r|`n" | Where-Object { $_ -like '*[[]SENF*' }).Count
        knoepfe = @([SmProbe.W]::Kinder($h) | Where-Object { [SmProbe.W]::Klasse($_) -match 'BUTTON' } | ForEach-Object { Falt ([SmProbe.W]::Text($_)) } | Where-Object { $_ }) }
}

if ($Modus -eq 'mikro') {
    $basis = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone'
    if (-not (Test-Path $basis)) { Ende 'fehler' 'Mikrofonanzeige-Schluessel fehlt (unbekannt -> KaiScribe fuegt nie ein)' }
    $apps = @()
    foreach ($k in @(Get-ChildItem $basis -ErrorAction SilentlyContinue) + @(Get-ChildItem (Join-Path $basis 'NonPackaged') -ErrorAction SilentlyContinue)) {
        $p = Get-ItemProperty -LiteralPath $k.PSPath -ErrorAction SilentlyContinue
        if ($null -eq $p -or $null -eq $p.LastUsedTimeStart) { continue }
        $a = [int64]$p.LastUsedTimeStart; $b = [int64]$p.LastUsedTimeStop
        $apps += [ordered]@{ app = ($k.PSChildName -split '#')[-1]; start = $(if ($a -gt 0) { [DateTime]::FromFileTime($a).ToString('s') } else { '' })
            stop = $(if ($b -gt 0) { [DateTime]::FromFileTime($b).ToString('s') } else { '' }); in_benutzung = ($a -gt 0 -and ($b -eq 0 -or $b -lt $a)) }
    }
    $erg.apps = $apps
    Ende 'ok' ('{0} App(s), CASSpeechMagic dabei: {1}' -f $apps.Count, [bool]($apps | Where-Object { $_.app -match 'CASSpeechMagic' }))
}
if ($Modus -eq 'warnung') {
    $w = @(Get-Warnung)
    $erg.warnung = @($w | ForEach-Object { [ordered]@{ titel = $_.titel; texte = $_.texte } })
    Ende 'ok' ('{0} Warnfenster' -f $w.Count)
}
$h = Get-Diktat
if ($h -eq [IntPtr]::Zero) { Ende 'kein_fenster' ('kein Diktatfenster User: ' + $Kuerzel) }
$l = Lies $h
if ($null -eq $l) { Ende 'fehler' 'kein RichEdit im Diktatfenster' }
$erg.feld = $l
if ($Modus -eq 'lesen') { Ende 'ok' 'gelesen' }
# fertig
if (-not $l.text.Contains($Marke)) { Ende 'abbruch' ('Marke "' + $Marke + '" nicht im Text - kein Testdiktat, nichts gedrueckt') }
$k = @([SmProbe.W]::Kinder($h) | Where-Object { [SmProbe.W]::Klasse($_) -match 'BUTTON' -and (Falt ([SmProbe.W]::Text($_))) -eq 'fertig stellen' })
if ($k.Count -ne 1) { Ende 'fehler' ('Knopf "Fertig stellen" nicht eindeutig: ' + $k.Count) }
$uhr = [Diagnostics.Stopwatch]::StartNew()
[void][SmProbe.W]::Klick($k[0])
while ($uhr.Elapsed.TotalSeconds -lt $WarteS -and [SmProbe.W]::IsWindow($h) -and [SmProbe.W]::IsWindowVisible($h)) { Start-Sleep -Milliseconds 300 }
$erg.zu_s = [math]::Round($uhr.Elapsed.TotalSeconds, 1)
if ([SmProbe.W]::IsWindow($h) -and [SmProbe.W]::IsWindowVisible($h)) { Ende 'fenster_offen' ('Diktatfenster nach ' + $WarteS + ' s noch offen (Dialog?)') }
$w = @()
$t0 = $uhr.Elapsed.TotalSeconds
while ($uhr.Elapsed.TotalSeconds - $t0 -lt 10 -and $w.Count -eq 0) { Start-Sleep -Milliseconds 500; $w = @(Get-Warnung) }
$erg.warnung_s = [math]::Round($uhr.Elapsed.TotalSeconds - $t0, 1)
$erg.warnung = @($w | ForEach-Object { [ordered]@{ titel = $_.titel; texte = $_.texte } })
foreach ($x in $w) { [void][SmProbe.W]::Zu($x.h) }
if ($w.Count -eq 0) { Ende 'keine_warnung' 'Diktat zu, aber kein KaiScribe-Warnfenster in 10 s' }
Ende 'ok' 'Diktat fertig gestellt, Warnfenster gesehen und geschlossen'
