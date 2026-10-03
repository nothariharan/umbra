$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$rev = 'b013f5e17143'
python scripts/lever.py stop 2>$null | Out-Null
$buildLog = python scripts/lever.py build --stage 2 --rev $rev 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) { Write-Error $buildLog; exit 1 }
$m = [regex]::Match($buildLog, 'built (umbra/stage-2:[^\s]+)')
if (-not $m.Success) { Write-Error "no image tag in build output"; exit 1 }
$tag = $m.Groups[1].Value
$name = 'umbra-certifier-replay50489'
cmd /c "docker rm -f $name 2>nul" | Out-Null
$cid = cmd /c "docker run -d --name $name --cpus 2 --memory 2g -e PORT=8080 -p 127.0.0.1:50489:8080 $tag"
if ($LASTEXITCODE -ne 0 -or -not $cid) { exit 1 }
if ($LASTEXITCODE -ne 0) { exit 1 }
$deadline = (Get-Date).AddSeconds(60)
while ((Get-Date) -lt $deadline) {
  try {
    $r = Invoke-WebRequest -Uri 'http://127.0.0.1:50489/health' -TimeoutSec 2 -UseBasicParsing
    if ($r.StatusCode -eq 200) { exit 0 }
  } catch { Start-Sleep -Milliseconds 250 }
}
docker logs --tail 40 $name
exit 1
