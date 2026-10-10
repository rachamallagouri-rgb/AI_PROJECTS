$ErrorActionPreference = "Stop"
$GradleVersion = "9.4.1"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Tools = Join-Path $ProjectRoot ".tools"
$Zip = Join-Path $Tools "gradle-$GradleVersion-bin.zip"
$GradleHome = Join-Path $Tools "gradle-$GradleVersion"

New-Item -ItemType Directory -Force -Path $Tools | Out-Null

# Create local.properties automatically for the standard Android SDK location.
$LocalProps = Join-Path $ProjectRoot "local.properties"
if (-not (Test-Path $LocalProps)) {
    $Sdk = $env:ANDROID_SDK_ROOT
    if (-not $Sdk) { $Sdk = Join-Path $env:LOCALAPPDATA "Android\Sdk" }
    if (-not (Test-Path $Sdk)) {
        throw "Android SDK not found. Install Android Studio SDK Platform 36 first."
    }
    $EscapedSdk = $Sdk.Replace("\", "\\")
    "sdk.dir=$EscapedSdk" | Set-Content -Encoding ASCII $LocalProps
}

if (-not (Test-Path $GradleHome)) {
    Write-Host "Downloading Gradle $GradleVersion..."
    Invoke-WebRequest "https://services.gradle.org/distributions/gradle-$GradleVersion-bin.zip" -OutFile $Zip
    Expand-Archive -Path $Zip -DestinationPath $Tools -Force
}

$Gradle = Join-Path $GradleHome "bin\gradle.bat"
& $Gradle wrapper --gradle-version $GradleVersion
if ($LASTEXITCODE -ne 0) { throw "Gradle wrapper generation failed." }

& (Join-Path $ProjectRoot "gradlew.bat") --version
if ($LASTEXITCODE -ne 0) { throw "Gradle wrapper verification failed." }

Write-Host "Gradle wrapper ready. Next: .\gradlew.bat :app:assembleDebug"
