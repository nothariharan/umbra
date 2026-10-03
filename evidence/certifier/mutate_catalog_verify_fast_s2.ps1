$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$rev = 'b013f5e17143'
$mutants = @(
  'm01_skip_available_balance.patch',
  'm02_ignore_holds.patch',
  'm03_idempotency_no_replay.patch'
)
foreach ($m in $mutants) {
  python scripts/lever.py mutate --stage 2 --mutant "mutants/stage-2/$m" --rev $rev --suites verifier,breaker
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
Write-Host 'mutation score 3/3 (verifier,breaker per mutant; official on clean build)'
exit 0
