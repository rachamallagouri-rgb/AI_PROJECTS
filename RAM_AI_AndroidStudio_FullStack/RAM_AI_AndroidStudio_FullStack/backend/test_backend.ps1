$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$Py = if (Test-Path ".venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { "py" }
& $Py -m compileall app
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Backend Python syntax check passed."
