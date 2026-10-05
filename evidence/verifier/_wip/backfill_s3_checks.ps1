# Record passing evidence for every registered S3-C* check at SUBMIT_REV via record.py.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'verifier'
$env:SUBMIT_REV = if ($env:SUBMIT_REV) { $env:SUBMIT_REV } else { '475ca690ab88' }
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'

$checks = @(
    'S3-C1', 'S3-C2', 'S3-C3', 'S3-C4', 'S3-C5', 'S3-C6', 'S3-C7', 'S3-C8', 'S3-C9', 'S3-C10',
    'S3-C11', 'S3-C12', 'S3-C13', 'S3-C14', 'S3-C15', 'S3-C16', 'S3-C17', 'S3-C18', 'S3-C19', 'S3-C20',
    'S3-C21', 'S3-C22', 'S3-C23', 'S3-C24', 'S3-C25', 'S3-C26', 'S3-C27', 'S3-C28', 'S3-C29', 'S3-C30'
)

$failed = @()
foreach ($c in $checks) {
    Write-Host "=== recording $c ==="
    $run = "powershell -NoProfile -File evidence/verifier/run_s3_check.ps1 -Check $c"
    $timeout = if ($c -in @('S3-C17', 'S3-C23', 'S3-C30')) { 1200 } else { 600 }
    & $py scripts/record.py evidence --seat verifier --check $c --run $run --timeout $timeout
    if ($LASTEXITCODE -ne 0) {
        $failed += $c
        Write-Warning "FAILED $c"
    }
}

Write-Host '=== official isolated stage 3 ==='
& $py scripts/lever.py checks --suite official --stage 3 --rev $env:SUBMIT_REV --isolated
if ($LASTEXITCODE -ne 0) { $failed += 'official' }

& $py scripts/record.py status --stage 3 --rev $env:SUBMIT_REV
if ($failed.Count -gt 0) {
    Write-Error "backfill failed checks: $($failed -join ', ')"
}
exit 0
