Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'uireviewer'
$env:SUBMIT_REV = 'b013f5e17143'
& powershell -NoProfile -File evidence/verifier/repro_s2_c6.ps1
