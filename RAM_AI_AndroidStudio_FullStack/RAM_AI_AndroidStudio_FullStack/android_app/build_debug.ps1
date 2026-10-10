$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
if (-not (Test-Path ".\gradlew.bat")) {
    & ".\bootstrap_gradle.ps1"
}
& ".\gradlew.bat" clean :app:assembleDebug --stacktrace
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "APK: app\build\outputs\apk\debug\app-debug.apk"
