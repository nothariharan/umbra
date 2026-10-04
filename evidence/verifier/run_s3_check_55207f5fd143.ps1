param([Parameter(Mandatory = $true)][string]$Check)
$env:SUBMIT_REV = '55207f5fd143'
& (Join-Path $PSScriptRoot 'run_s3_check.ps1') -Check $Check
exit $LASTEXITCODE
