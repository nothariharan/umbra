param([string]$Rev = $env:SUBMIT_REV, [string]$Module = '')
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'breaker'
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'
$rev = if ($Rev) { $Rev } else { throw 'SUBMIT_REV is required' }
$boot = & $py scripts/lever.py boot --stage 4 --rev $rev 2>&1 | Out-String
if ($boot -notmatch 'BASE_URL=(\S+)') { throw "no BASE_URL in boot output: $boot" }
$env:BASE_URL = $Matches[1]
if ($Module) {
  & $py -m pytest -q -p no:cacheprovider "attacks/stage-4/$Module"
} else {
  & $py -m pytest -q -p no:cacheprovider attacks/stage-4
}
$code = $LASTEXITCODE
& $py scripts/lever.py stop | Out-Null
exit $code
