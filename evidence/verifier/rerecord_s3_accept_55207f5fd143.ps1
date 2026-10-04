Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'verifier'
$Pin = '55207f5fd143'
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'
$newIds = @()

function Invoke-Record {
    param([string]$Check, [string]$Run, [int]$Timeout = 600)
    Write-Host "=== $Check ==="
    & $py scripts/record.py evidence --seat verifier --check $Check --run $Run --timeout $Timeout
    if ($LASTEXITCODE -ne 0) { throw "record failed $Check" }
    $last = Get-Content record/verifier.jsonl -Tail 1 | ConvertFrom-Json
    $script:newIds += $last.id
    Write-Host "recorded $($last.id) exit=$($last.exit) rev=$($last.rev)"
}

$official = "python scripts/lever.py checks --suite official --stage 3 --rev $Pin --isolated"
Invoke-Record -Check 'S3-C2' -Run $official -Timeout 900

$suiteRun = "powershell -NoProfile -File evidence/verifier/run_s3_pytest_55207f5fd143.ps1 -Node verify/stage-3"
Invoke-Record -Check 'S3-C3' -Run $suiteRun -Timeout 900

$checks = @(
    'S3-C1', 'S3-C4', 'S3-C5', 'S3-C6', 'S3-C7', 'S3-C8', 'S3-C9', 'S3-C10',
    'S3-C11', 'S3-C12', 'S3-C13', 'S3-C14', 'S3-C15', 'S3-C16', 'S3-C17', 'S3-C18', 'S3-C19', 'S3-C20',
    'S3-C21', 'S3-C22', 'S3-C23', 'S3-C24', 'S3-C25', 'S3-C26', 'S3-C27', 'S3-C28', 'S3-C29', 'S3-C30'
)
foreach ($c in $checks) {
    $run = "powershell -NoProfile -File evidence/verifier/run_s3_check_55207f5fd143.ps1 -Check $c"
    $timeout = if ($c -in @('S3-C17', 'S3-C23', 'S3-C30')) { 1200 } else { 600 }
    Invoke-Record -Check $c -Run $run -Timeout $timeout
}

Write-Host ($newIds -join ',')
$newIds | Set-Content evidence/verifier/rerecord_55207f5_ids.txt
exit 0
