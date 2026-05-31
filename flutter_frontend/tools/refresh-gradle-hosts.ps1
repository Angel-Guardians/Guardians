# Regenerate C:\Android\gradle-hosts.txt with current IPv4 addresses for the
# hosts the Android/Gradle build contacts.
#
# Why this exists: on this machine the JVM's own DNS/IPv6 path to Gradle/Google/
# Maven CDNs is broken ("UnknownHostException" / "Network is unreachable"),
# while IPv4 works. We feed Java a static hosts file via
# `-Djdk.net.hosts.file=...` (see android/gradle.properties). CDN IPs drift over
# time, so rerun this if a build suddenly fails with UnknownHostException or
# "Network is unreachable".
#
# Usage:  powershell -ExecutionPolicy Bypass -File tools\refresh-gradle-hosts.ps1

$ErrorActionPreference = 'SilentlyContinue'
$hosts = @(
  'plugins.gradle.org', 'plugins-artifacts.gradle.org',
  'dl.google.com', 'maven.google.com',
  'repo.maven.apache.org', 'repo1.maven.org',
  'services.gradle.org', 'repo.gradle.org',
  'storage.googleapis.com', 'jcenter.bintray.com'
)
$lines = @()
foreach ($h in $hosts) {
  $ip = curl.exe -4 -s -o NUL --max-time 12 "https://$h/" -w "%{remote_ip}" 2>$null
  if ($ip -and $ip -notmatch ':') {
    $lines += "$ip $h"
    Write-Host ("{0,-32} -> {1}" -f $h, $ip)
  } else {
    Write-Host ("{0,-32} -> UNRESOLVED (skipped)" -f $h) -ForegroundColor Yellow
  }
}
$dir = 'C:\Android'
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
$file = Join-Path $dir 'gradle-hosts.txt'
$lines -join "`n" | Out-File -Encoding ascii $file
Write-Host "`nWrote $file" -ForegroundColor Green
