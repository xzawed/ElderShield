# Lab: open enrollment window, enroll a device token, push prefs to USB device, enqueue sync.
# Requires: backend on 127.0.0.1:8765 with ELDERSHIELD_ENROLL_SKIP_INTEGRITY=1, adb device.
param(
    [string]$Serial = "",
    [string]$AdminKey = "replace-with-strong-admin-key",
    [string]$BaseUrl = "http://127.0.0.1:8765",
    [string]$Adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $Adb)) { throw "adb not found: $Adb" }

if (-not $Serial) {
    $lines = & $Adb devices | Where-Object { $_ -match "\tdevice$" -and $_ -notmatch "emulator-" }
    if (-not $lines) { throw "No physical device in 'device' state" }
    $Serial = ($lines[0] -split "\s+")[0]
}

Write-Host "serial=$Serial"
& $Adb -s $Serial reverse tcp:8765 tcp:8765 | Out-Null

$admin = @{ "X-API-Key" = $AdminKey }
Invoke-RestMethod -Uri "$BaseUrl/api/v1/admin/enrollment-window" -Method POST -Headers $admin `
    -ContentType "application/json" -Body '{"enabled":true,"ttlMinutes":30}' | Out-Null

$enroll = Invoke-RestMethod -Uri "$BaseUrl/api/v1/devices/enroll" -Method POST `
    -ContentType "application/json" -Body '{"appVersion":"0.2.0","model":"lab-enroll-ps1"}'
Write-Host "enrolled $($enroll.deviceUuid)"

$xml = @"
<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
  <string name="base_url">$BaseUrl</string>
  <string name="device_uuid">$($enroll.deviceUuid)</string>
  <string name="device_api_key">$($enroll.deviceToken)</string>
</map>
"@
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($xml))
& $Adb -s $Serial shell "echo $b64 | base64 -d > /data/local/tmp/eldershield.xml"
& $Adb -s $Serial shell "run-as com.eldershield mkdir -p shared_prefs"
& $Adb -s $Serial shell "run-as com.eldershield cp /data/local/tmp/eldershield.xml shared_prefs/eldershield.xml"
& $Adb -s $Serial shell am force-stop com.eldershield
& $Adb -s $Serial shell am start -n com.eldershield/.ui.MainActivity | Out-Null
Start-Sleep -Seconds 2
# Tap SAVE & SYNC (approx; debug layout)
& $Adb -s $Serial shell input tap 720 780
Start-Sleep -Seconds 10

$devs = Invoke-RestMethod -Uri "$BaseUrl/api/v1/admin/devices" -Headers $admin
$row = $devs | Where-Object { $_.deviceUuid -eq $enroll.deviceUuid }
if (-not $row) { throw "device row missing" }
Write-Host "lastSyncAt=$($row.lastSyncAt) lastRuleVersion=$($row.lastRuleVersion)"

Invoke-RestMethod -Uri "$BaseUrl/api/v1/admin/enrollment-window" -Method POST -Headers $admin `
    -ContentType "application/json" -Body '{"enabled":false}' | Out-Null
Write-Host "enrollment window closed"
