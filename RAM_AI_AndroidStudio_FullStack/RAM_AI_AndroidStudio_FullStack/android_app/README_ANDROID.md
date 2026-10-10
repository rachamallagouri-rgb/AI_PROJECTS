# RAM AI — Android Studio

## Toolchain
- Android Studio Rabbit 1 / compatible recent Android Studio
- JDK 17
- Android SDK Platform 36
- Android Gradle Plugin 9.2.0
- Gradle 9.4.1
- minSdk 26, targetSdk 36

## First run on Windows
1. Open this `android_app` folder in Android Studio.
2. Install Android SDK Platform 36 if prompted.
3. In PowerShell from this folder:
   `powershell -ExecutionPolicy Bypass -File .\bootstrap_gradle.ps1`
4. Start the backend on port 8000.
5. Run an emulator.
6. Build:
   `.\gradlew.bat clean :app:assembleDebug`

The debug app uses `http://10.0.2.2:8000` to reach a backend running on the same Windows PC.
For a physical phone, build with a reachable HTTPS backend:
`\.\gradlew.bat :app:assembleRelease -PRAM_AI_API_URL=https://api.yourdomain.com`

Do not publish a release that points to `10.0.2.2` or cleartext HTTP.
