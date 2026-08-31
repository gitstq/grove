# One-key cross-platform build for Grove (Windows PowerShell).
# Runs compile checks + unit tests, then builds a wheel and sdist into dist\.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$Py = if ($env:PYTHON) { $env:PYTHON } else { "python" }

Write-Host "==> [1/3] byte-compile"
& $Py -m compileall -q src tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> [2/3] unit tests"
& $Py -m unittest discover -s tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> [3/3] build wheel + sdist"
& $Py -m pip install --quiet --upgrade build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Py -m build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Done. Artifacts:"
Get-ChildItem dist | Select-Object Name
