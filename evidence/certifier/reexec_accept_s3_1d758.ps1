$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$ids = @(
  'E-verifier-240','E-verifier-243',
  'E-verifier-244','E-verifier-245','E-verifier-246','E-verifier-247','E-verifier-248','E-verifier-249',
  'E-verifier-250','E-verifier-251','E-verifier-252','E-verifier-253','E-verifier-254','E-verifier-255',
  'E-verifier-256','E-verifier-257','E-verifier-258','E-verifier-259','E-verifier-260','E-verifier-261',
  'E-verifier-262','E-verifier-263','E-verifier-264','E-verifier-265','E-verifier-266','E-verifier-267',
  'E-verifier-268','E-verifier-269','E-verifier-270','E-verifier-271',
  'E-breaker-54','E-breaker-55','E-breaker-56','E-breaker-57','E-breaker-58','E-breaker-59','E-breaker-60',
  'E-uireviewer-26'
)
foreach ($id in $ids) {
  python scripts/lever.py reexec --evidence $id
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
exit 0
