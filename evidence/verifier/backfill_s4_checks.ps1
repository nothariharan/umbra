# Record passing evidence for every registered S4-C* check at SUBMIT_REV via record.py.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'verifier'
$env:SUBMIT_REV = if ($env:SUBMIT_REV) { $env:SUBMIT_REV } else { '10d2be5fa9c6' }
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'
$runScript = "evidence/verifier/run_s4_check_10d2be5fa9c6.ps1"

& $py scripts/lever.py stop 2>&1 | Out-Null

$checks = @(
    'S4-C1', 'S4-C2', 'S4-C3', 'S4-C4', 'S4-C5', 'S4-C6', 'S4-C7', 'S4-C8', 'S4-C9', 'S4-C10',
    'S4-C11', 'S4-C12', 'S4-C13', 'S4-C14', 'S4-C15', 'S4-C16', 'S4-C17', 'S4-C18', 'S4-C19', 'S4-C20',
    'S4-C21', 'S4-C22', 'S4-C23', 'S4-C24', 'S4-C25', 'S4-C26', 'S4-C27', 'S4-C28'
)

$failed = @()
foreach ($c in $checks) {
    Write-Host "=== recording $c ==="
    $run = "powershell -NoProfile -File $runScript -Check $c"
    $timeout = switch ($c) {
        'S4-C25' { 1200 }
        'S4-C27' { 1200 }
        'S4-C28' { 900 }
        default { 600 }
    }
    & $py scripts/record.py evidence --seat verifier --check $c --run $run --timeout $timeout
    if ($LASTEXITCODE -ne 0) {
        $failed += $c
        Write-Warning "FAILED $c"
    }
}

& $py scripts/record.py status --stage 4 --rev $env:SUBMIT_REV
if ($failed.Count -gt 0) {
    Write-Error "backfill failed checks: $($failed -join ', ')"
}
exit 0
