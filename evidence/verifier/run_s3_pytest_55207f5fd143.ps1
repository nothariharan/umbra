param([Parameter(Mandatory = $true)][string]$Node)
$env:SUBMIT_REV = '55207f5fd143'
& (Join-Path $PSScriptRoot 'run_s3_pytest.ps1') -Node $Node
exit $LASTEXITCODE
