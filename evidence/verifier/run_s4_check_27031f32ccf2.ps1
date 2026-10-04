param([Parameter(Mandatory = $true)][string]$Check)
$env:SUBMIT_REV = '27031f32ccf2'
& (Join-Path $PSScriptRoot 'run_s4_check.ps1') -Check $Check
exit $LASTEXITCODE
