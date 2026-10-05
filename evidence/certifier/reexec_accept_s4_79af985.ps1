$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$verifier = @('E-verifier-437', 'E-verifier-438')
$breaker = 83..93 | ForEach-Object { "E-breaker-$_" }
$uireviewer = @(
  'E-uireviewer-65','E-uireviewer-66','E-uireviewer-67','E-uireviewer-72','E-uireviewer-73',
  'E-uireviewer-74','E-uireviewer-75','E-uireviewer-76','E-uireviewer-77','E-uireviewer-78',
  'E-uireviewer-79','E-uireviewer-80','E-uireviewer-64'
)
foreach ($id in ($verifier + $breaker + $uireviewer)) {
  python scripts/lever.py reexec --evidence $id
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
python scripts/lever.py stop 2>$null | Out-Null
exit 0
