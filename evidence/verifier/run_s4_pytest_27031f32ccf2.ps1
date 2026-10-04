param([Parameter(Mandatory = $true)][string]$Node)
$env:SUBMIT_REV = '27031f32ccf2'
& (Join-Path $PSScriptRoot 'run_s4_pytest.ps1') -Node $Node
exit $LASTEXITCODE
