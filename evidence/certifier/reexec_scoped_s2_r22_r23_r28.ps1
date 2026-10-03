$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$ids = @(
  'E-verifier-61','E-verifier-56',
  'E-breaker-21','E-breaker-22','E-breaker-23','E-breaker-24','E-breaker-25','E-breaker-27',
  'E-uireviewer-10','E-uireviewer-11'
)
foreach ($id in $ids) {
  if ($id -like 'E-breaker-*') { continue }
  python scripts/lever.py reexec --evidence $id
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& (Join-Path $PSScriptRoot 'boot_breaker_replay_50489.ps1')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
foreach ($id in $ids) {
  if ($id -notlike 'E-breaker-*') { continue }
  python scripts/lever.py reexec --evidence $id
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
cmd /c "docker rm -f umbra-certifier-replay50489 2>nul" | Out-Null
python scripts/lever.py stop 2>$null | Out-Null
exit 0
