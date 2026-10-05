param([Parameter(Mandatory = $true)][string]$Check)
$env:SUBMIT_REV = '79af98560dd9'
& (Join-Path $PSScriptRoot 'run_s4_check.ps1') -Check $Check
exit $LASTEXITCODE
