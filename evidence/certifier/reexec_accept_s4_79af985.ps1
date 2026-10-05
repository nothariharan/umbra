$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
# Latest ACCEPT @ 79af98560dd9 per seat (S4-U10 verifier; uireviewer refresh E-86..98)
$verifier = @('E-verifier-437', 'E-verifier-438')
$breaker = 83..93 | ForEach-Object { "E-breaker-$_" }
$uireviewer = 86..98 | ForEach-Object { "E-uireviewer-$_" }
foreach ($id in ($verifier + $breaker + $uireviewer)) {
  python scripts/lever.py reexec --evidence $id
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
python scripts/lever.py stop 2>$null | Out-Null
exit 0
