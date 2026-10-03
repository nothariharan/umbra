param(
    [Parameter(Mandatory = $true)][int]$Stage,
    [Parameter(Mandatory = $true)][string]$Rev,
    [Parameter(Mandatory = $true)][string[]]$Files
)

$ErrorActionPreference = 'Stop'
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $root

$bootOutput = & $py 'scripts/lever.py' 'boot' '--stage' "$Stage" '--rev' $Rev 2>&1 | Out-String
if ($bootOutput -notmatch 'BASE_URL=(\S+)') {
    Write-Output $bootOutput
    Write-Error 'lever boot did not report a BASE_URL'
    exit 2
}
$baseUrl = $Matches[1].Trim()
$env:BASE_URL = $baseUrl
Write-Output "BASE_URL=$baseUrl"

$code = 1
try {
    & $py -m pytest -q -p no:cacheprovider @Files
    $code = $LASTEXITCODE
}
finally {
    & $py 'scripts/lever.py' 'stop' 2>&1 | Out-Null
}
exit $code
