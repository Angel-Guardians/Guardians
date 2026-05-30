<#
  Path B - install the Android command-line toolchain and build the Guardian
  Watch APK WITHOUT Android Studio.

  Run from a normal (non-admin) PowerShell:
      powershell -ExecutionPolicy Bypass -File D:\Projects\Guardians\watch\setup-android.ps1

  Safe to re-run: it skips downloads/installs that are already present.
#>
$ErrorActionPreference = "Stop"

# ---- config (edit if your paths differ) ------------------------------------
$Sdk     = "C:\Android\Sdk"
$Jdk     = "$env:USERPROFILE\.jdks\openjdk-21.0.2"   # the JDK already on this machine
$Proj    = "D:\Projects\Guardians\watch"
$CliUrl  = "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
$WrapUrl = "https://raw.githubusercontent.com/gradle/gradle/v8.7.0/gradle/wrapper/gradle-wrapper.jar"
$Tmp     = Join-Path $env:TEMP "guardian-android-setup"

Write-Host "SDK   : $Sdk"
Write-Host "JDK   : $Jdk"
Write-Host "Watch : $Proj"

if (-not (Test-Path "$Jdk\bin\java.exe")) {
    throw "JDK not found at $Jdk - edit the `$Jdk variable at the top of this script."
}
New-Item -ItemType Directory -Force -Path $Sdk, $Tmp | Out-Null

# ---- 1. command-line tools -> $Sdk\cmdline-tools\latest --------------------
# (the zip nests a 'cmdline-tools' folder; sdkmanager REQUIRES it under \latest)
if (-not (Test-Path "$Sdk\cmdline-tools\latest\bin\sdkmanager.bat")) {
    $zip = Join-Path $Tmp "cmdline-tools.zip"
    if (-not (Test-Path $zip)) {
        Write-Host "Downloading Android command-line tools (~150 MB)..."
        curl.exe -L -o $zip $CliUrl
    }
    Write-Host "Extracting..."
    if (Test-Path "$Tmp\cmdline-tools") { Remove-Item "$Tmp\cmdline-tools" -Recurse -Force }
    Expand-Archive -Path $zip -DestinationPath $Tmp -Force
    New-Item -ItemType Directory -Force -Path "$Sdk\cmdline-tools\latest" | Out-Null
    Move-Item -Path "$Tmp\cmdline-tools\*" -Destination "$Sdk\cmdline-tools\latest" -Force
} else {
    Write-Host "cmdline-tools already present - skipping."
}

# ---- 2. environment variables (persisted for future shells + this session) -
[Environment]::SetEnvironmentVariable("ANDROID_HOME", $Sdk, "User")
[Environment]::SetEnvironmentVariable("JAVA_HOME",    $Jdk, "User")
$env:ANDROID_HOME = $Sdk
$env:JAVA_HOME    = $Jdk

$add = "$Sdk\cmdline-tools\latest\bin;$Sdk\platform-tools"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*cmdline-tools\latest\bin*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$add", "User")
}
$env:Path = "$env:Path;$add"

# point this project's Gradle build straight at the SDK
"sdk.dir=$($Sdk -replace '\\','\\')" | Out-File -FilePath "$Proj\local.properties" -Encoding ascii
Write-Host "Wrote $Proj\local.properties"

# ---- 3. accept licenses + install the packages this project needs ----------
$sdkmgr = "$Sdk\cmdline-tools\latest\bin\sdkmanager.bat"
Write-Host "Accepting SDK licenses..."
1..30 | ForEach-Object { "y" } | & $sdkmgr --licenses
Write-Host "Installing platform-tools, android-34, build-tools 34.0.0..."
& $sdkmgr "platform-tools" "platforms;android-34" "build-tools;34.0.0"

# ---- 4. supply the Gradle wrapper jar (binary, not committed) --------------
$wrapJar = "$Proj\gradle\wrapper\gradle-wrapper.jar"
if (-not (Test-Path $wrapJar)) {
    Write-Host "Fetching gradle-wrapper.jar..."
    curl.exe -L -o $wrapJar $WrapUrl
}

# ---- 5. build the debug APK ------------------------------------------------
Set-Location $Proj
Write-Host "Building (first run also downloads Gradle 8.7 + dependencies)..."
& "$Proj\gradlew.bat" :app:assembleDebug

$apk = "$Proj\app\build\outputs\apk\debug\app-debug.apk"
if (Test-Path $apk) {
    Write-Host ""
    Write-Host "BUILD OK -> $apk" -ForegroundColor Green
    Write-Host "Install to a connected watch:  adb install -r `"$apk`""
} else {
    throw "Build finished but no APK at $apk"
}
