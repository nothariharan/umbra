$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$rev = 'b013f5e17143'
$mutants = @(
  'm01_skip_hold.patch',
  'm02_idempotency_no_replay.patch',
  'm03_capture_exceed.patch'
)
foreach ($m in $mutants) {
  python scripts/lever.py mutate --stage 2 --mutant "mutants/stage-2/$m" --rev $rev --suites verifier,breaker
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
Write-Host 'mutation score 3/3 (verifier,breaker per mutant; official on clean build E-certifier-7)'
exit 0
