Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'uireviewer'
$rev = if ($env:SUBMIT_REV) { $env:SUBMIT_REV } else { '475ca690ab88' }
$boot = & python scripts/lever.py boot --stage 3 --rev $rev 2>&1 | Out-String
if ($boot -notmatch 'BASE_URL=(\S+)') { Write-Error "boot failed: $boot" }
$url = $Matches[1]
try {
  & python scripts/lever.py checks --suite uireviewer --stage 3 --base-url $url
  exit $LASTEXITCODE
} finally {
  & python scripts/lever.py stop 2>&1 | Out-Null
}
