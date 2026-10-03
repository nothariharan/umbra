Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'uireviewer'
$rev = 'b013f5e17143'
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'
$boot = & $py scripts/lever.py boot --stage 2 --rev $rev 2>&1 | Out-String
if ($boot -notmatch 'BASE_URL=(\S+)') { throw "no BASE_URL" }
$env:BASE_URL = $Matches[1]
& $py -m pytest -q review/stage-2/test_s2_ui_r28_r29_authorizations.py
$code = $LASTEXITCODE
& $py scripts/lever.py stop | Out-Null
exit $code
