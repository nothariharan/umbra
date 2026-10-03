# Record passing evidence for every registered S1-C* check at SUBMIT_REV via record.py.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'verifier'
$env:SUBMIT_REV = if ($env:SUBMIT_REV) { $env:SUBMIT_REV } else { '1125eee49810' }
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'

$checks = @(
    'S1-C1', 'S1-C2', 'S1-C3', 'S1-C4', 'S1-C5', 'S1-C6', 'S1-C9', 'S1-C10',
    'S1-C11', 'S1-C12', 'S1-C13', 'S1-C14', 'S1-C15', 'S1-C16', 'S1-C17', 'S1-C18',
    'S1-C20', 'S1-C21', 'S1-C22', 'S1-C23', 'S1-C24', 'S1-C25', 'S1-C26', 'S1-C27',
    'S1-C28', 'S1-C29', 'S1-C30', 'S1-C31', 'S1-C32', 'S1-C33', 'S1-C34', 'S1-C35'
)

$failed = @()
foreach ($c in $checks) {
    Write-Host "=== recording $c ==="
    $run = "powershell -NoProfile -File evidence/verifier/run_s1_check.ps1 -Check $c"
    & $py scripts/record.py evidence --seat verifier --check $c --run $run --timeout 600
    if ($LASTEXITCODE -ne 0) {
        $failed += $c
        Write-Warning "FAILED $c"
    }
}

& $py scripts/record.py status --stage 1 --rev $env:SUBMIT_REV
if ($failed.Count -gt 0) {
    Write-Error "backfill failed checks: $($failed -join ', ')"
}
exit 0
