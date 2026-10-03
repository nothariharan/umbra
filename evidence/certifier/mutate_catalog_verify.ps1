$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$rev = '1125eee49810'
$mutants = @(
  'm01_pair_hide_public.patch',
  'm02_skip_insufficient.patch',
  'm03_idempotency_no_replay.patch'
)
foreach ($m in $mutants) {
  python scripts/lever.py mutate --stage 1 --mutant "mutants/stage-1/$m" --rev $rev --suites official,verifier,breaker
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
Write-Host 'mutation score 3/3 (official,verifier,breaker per mutant)'
exit 0
