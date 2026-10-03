Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'verifier'
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'
$rev = if ($env:SUBMIT_REV) { $env:SUBMIT_REV } else { 'b013f5e17143' }
$boot = & $py scripts/lever.py boot --stage 2 --rev $rev 2>&1 | Out-String
if ($boot -notmatch 'BASE_URL=(\S+)') { throw "no BASE_URL in boot output" }
$env:BASE_URL = $Matches[1]
& $py -c "import httpx; httpx.post('$($env:BASE_URL)/_test/reset', json={'currency':'EUR','minor_units':2,'users':[{'id':'u_ada','email':'ada@example.com','password':'correct horse','display_name':'Ada','handle':'ada','balance':10000},{'id':'u_bob','email':'bob@example.com','password':'correct horse','display_name':'Bob','handle':'bob','balance':2500},{'id':'u_cy','email':'cy@example.com','password':'correct horse','display_name':'Cy','handle':'cy','balance':500}]}, timeout=10).raise_for_status()"
& $py -m pytest -q verify/stage-2/test_s2_ui_flows.py::test_s2_c6_pay_form_no_double_submit_without_change
$code = $LASTEXITCODE
& $py scripts/lever.py stop | Out-Null
exit $code
