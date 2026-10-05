Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'verifier'
$env:SUBMIT_REV = if ($env:SUBMIT_REV) { $env:SUBMIT_REV } else { '79af98560dd9' }
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'
$runScript = 'evidence/verifier/run_s4_check_79af98560dd9.ps1'
& $py scripts/lever.py stop 2>&1 | Out-Null
$checks = @('S4-C1'); foreach ($n in 2..28) { $checks += "S4-RC$n" }
$failed = @()
foreach ($c in $checks) {
    Write-Host "=== recording $c ==="
    $timeout = switch ($c) { 'S4-RC25' {1200} 'S4-RC27' {1200} 'S4-RC28' {900} default {600} }
    & $py scripts/record.py evidence --seat verifier --check $c --run "powershell -NoProfile -File $runScript -Check $c" --timeout $timeout
    if ($LASTEXITCODE -ne 0) { $failed += $c }
}
& $py scripts/record.py status --stage 4 --rev $env:SUBMIT_REV
if ($failed.Count -gt 0) { Write-Error "backfill failed: $($failed -join ', ')" }
