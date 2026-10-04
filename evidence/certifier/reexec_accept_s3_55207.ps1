$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$ids = @(
  'E-verifier-272','E-verifier-273',
  'E-verifier-275','E-verifier-276','E-verifier-277','E-verifier-278','E-verifier-279',
  'E-verifier-280','E-verifier-281','E-verifier-282','E-verifier-283','E-verifier-284',
  'E-verifier-285','E-verifier-286','E-verifier-287','E-verifier-288','E-verifier-289',
  'E-verifier-290','E-verifier-291','E-verifier-292','E-verifier-293','E-verifier-294',
  'E-verifier-295','E-verifier-296','E-verifier-297','E-verifier-298','E-verifier-299',
  'E-verifier-300','E-verifier-301',
  'E-breaker-63',
  'E-uireviewer-30'
)
foreach ($id in $ids) {
  python scripts/lever.py reexec --evidence $id
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
exit 0
