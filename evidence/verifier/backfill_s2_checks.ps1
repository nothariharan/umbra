# Record passing evidence for every registered S2-C* check at SUBMIT_REV via record.py.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'verifier'
$env:SUBMIT_REV = if ($env:SUBMIT_REV) { $env:SUBMIT_REV } else { 'b013f5e17143' }
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'

$checks = @(
    'S2-C1', 'S2-C2', 'S2-C3', 'S2-C4', 'S2-C5', 'S2-C6', 'S2-C7', 'S2-C8', 'S2-C9', 'S2-C10',
    'S2-C11', 'S2-C12', 'S2-C13', 'S2-C14', 'S2-C15', 'S2-C16', 'S2-C17', 'S2-C18', 'S2-C19', 'S2-C20',
    'S2-C21', 'S2-C22', 'S2-C23', 'S2-C24', 'S2-C25', 'S2-C26', 'S2-C27', 'S2-C32'
)

$failed = @()
foreach ($c in $checks) {
    Write-Host "=== recording $c ==="
    $run = "powershell -NoProfile -File evidence/verifier/run_s2_check.ps1 -Check $c"
    $timeout = if ($c -in @('S2-C4', 'S2-C32', 'S2-C15')) { 1200 } else { 600 }
    & $py scripts/record.py evidence --seat verifier --check $c --run $run --timeout $timeout
    if ($LASTEXITCODE -ne 0) {
        $failed += $c
        Write-Warning "FAILED $c"
    }
}

& $py scripts/record.py status --stage 2 --rev $env:SUBMIT_REV
if ($failed.Count -gt 0) {
    Write-Error "backfill failed checks: $($failed -join ', ')"
}
exit 0
