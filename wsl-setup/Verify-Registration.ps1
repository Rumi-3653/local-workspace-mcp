# Verify-Registration.ps1 -- run OUTSIDE the Claude App container (one-shot scheduled task).
# Confirms the MCP registrations written from inside the app are visible to a plain process:
# ~/.claude.json mcpServers.local-workspace and ~/.codex/config.toml [mcp_servers.local-workspace],
# plus the WSL distro registration. ASCII only.
param([string]$Report = "D:\local-workspace-mcp\wsl-setup\verify-registration.report.txt")
$ErrorActionPreference = "Continue"
$log = New-Object System.Collections.Generic.List[string]
function Log([string]$s) { $log.Add($s) }
Log ("START " + (Get-Date -Format o) + " pid=" + $PID)
$cj = Join-Path $env:USERPROFILE ".claude.json"
$ct = Join-Path $env:USERPROFILE ".codex\config.toml"
foreach ($f in @($cj, $ct)) {
  if (Test-Path $f) {
    $h = (Get-FileHash $f -Algorithm SHA256).Hash
    $hit = (Select-String -Path $f -Pattern 'local-workspace' -SimpleMatch | Measure-Object).Count
    Log ("file=" + $f + " sha256=" + $h + " local-workspace-lines=" + $hit)
  } else { Log ("MISSING " + $f) }
}
[Console]::OutputEncoding = [System.Text.Encoding]::Unicode
$lv = & wsl.exe -l -v 2>&1
foreach ($line in $lv) { Log ("  wsl: " + ([string]$line).Trim()) }
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$who = & wsl.exe -d Ubuntu-24.04 --exec /usr/bin/id 2>&1
Log ("  id-in-distro: " + $who)
$x = & wsl.exe -d Ubuntu-24.04 --exec /usr/bin/test -x /home/user/.local/state/local-workspace-mcp/launch.sh
Log ("  launch.sh executable: exit=" + $LASTEXITCODE)
Log ("END " + (Get-Date -Format o))
$log | Set-Content -Path $Report -Encoding utf8
