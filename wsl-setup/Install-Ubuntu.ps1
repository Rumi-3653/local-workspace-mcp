# Install-Ubuntu.ps1 -- register a WSL Ubuntu distro for local-workspace-mcp.
# Runs OUTSIDE the Claude App MSIX container via a one-shot scheduled task, so the
# registration lands in the real HKCU\...\Lxss hive and not a virtualized copy.
# ASCII only (PowerShell 5.1 reads BOM-less non-ASCII files as mojibake).
param(
  [string]$Distro   = "Ubuntu-24.04",
  [string]$Location = "D:\WSL\Ubuntu-24.04",
  # When set, install from a pre-downloaded .wsl image instead of letting wsl.exe download
  # (its own download from releases.ubuntu.com stalled at ~144 MB on 2026-09-14).
  [string]$FromFile = "",
  [string]$Report   = "D:\local-workspace-mcp\wsl-setup\install-ubuntu.report.txt"
)
$ErrorActionPreference = "Continue"
$log = New-Object System.Collections.Generic.List[string]
function Log([string]$s) { $log.Add($s) }

Log ("START " + (Get-Date -Format o))
Log ("whoami=" + [Security.Principal.WindowsIdentity]::GetCurrent().Name)
Log ("pid=" + $PID + " host=" + $Host.Name)

# wsl.exe prints UTF-16LE when its stdout is a pipe; decode it as such.
[Console]::OutputEncoding = [System.Text.Encoding]::Unicode

New-Item -ItemType Directory -Force -Path $Location | Out-Null
$sw = [System.Diagnostics.Stopwatch]::StartNew()
if ($FromFile -ne "") {
  Log ("mode=from-file " + $FromFile + " size=" + (Get-Item $FromFile).Length)
  $out = & wsl.exe --install --from-file $FromFile --name $Distro --location $Location --no-launch 2>&1
} else {
  Log "mode=online"
  $out = & wsl.exe --install -d $Distro --no-launch --location $Location 2>&1
}
$code = $LASTEXITCODE
Log ("install exit=" + $code + " elapsed=" + [int]$sw.Elapsed.TotalSeconds + "s")
foreach ($line in $out) { Log ("  out: " + ([string]$line).Trim()) }

Log "--- wsl -l -v ---"
$lv = & wsl.exe -l -v 2>&1
foreach ($line in $lv) { Log ("  " + ([string]$line).Trim()) }

Log "--- HKCU Lxss ---"
try {
  Get-ChildItem "HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss" -ErrorAction Stop | ForEach-Object {
    $p = Get-ItemProperty $_.PSPath
    Log ("  " + $p.DistributionName + " | BasePath=" + $p.BasePath + " | Flags=" + $p.Flags + " | DefaultUid=" + $p.DefaultUid + " | RunOOBE=" + $p.RunOOBE)
  }
} catch { Log ("  reg error: " + $_.Exception.Message) }

Log "--- location listing ---"
try {
  Get-ChildItem $Location -Force -ErrorAction Stop | ForEach-Object { Log ("  " + $_.Name + " " + $_.Length) }
} catch { Log ("  dir error: " + $_.Exception.Message) }

Log ("END " + (Get-Date -Format o) + " exit=" + $code)
$log | Set-Content -Path $Report -Encoding utf8
exit $code
