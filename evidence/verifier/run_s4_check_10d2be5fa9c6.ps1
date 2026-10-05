param([Parameter(Mandatory = $true)][string]$Check)
$env:SUBMIT_REV = '10d2be5fa9c6'
& (Join-Path $PSScriptRoot 'run_s4_check.ps1') -Check $Check
exit $LASTEXITCODE
