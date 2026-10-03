Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'verifier'
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'
$boot = & $py scripts/lever.py boot --stage 1 --rev 97732094916a 2>&1 | Out-String
if ($boot -notmatch 'BASE_URL=(\S+)') { throw "no BASE_URL in boot output" }
$env:BASE_URL = $Matches[1]
& $py -m pytest -q verify/stage-1/test_s1_differential.py::test_s1_c31_differential_payments_match_reference
$code = $LASTEXITCODE
& $py scripts/lever.py stop | Out-Null
exit $code
