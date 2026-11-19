# Fail-open + silent UX on backend outage (emulator only). No physical PSTN.
# Expect: empty cache + dead API => Allow CN inbound; no ES notifications/toasts/dialogs.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
$Emu = "emulator-5554"
$Pkg = "com.eldershield"
$Apk = Join-Path $Root "android\app\build\outputs\apk\debug\app-debug.apk"
$Results = [System.Collections.Generic.List[object]]::new()

function Add-R([string]$Id, [string]$Status, [string]$Notes) {
  $Results.Add([pscustomobject]@{ id = $Id; status = $Status; notes = "$Notes" })
  Write-Host ("[{0}] {1} - {2}" -f $Id, $Status, $Notes)
}

function Assert-Emu {
  if ($Emu -notmatch '^emulator-') { throw "emulator only" }
  if (-not (& $Adb devices | Select-String "^$Emu\s+device")) { throw "emulator offline" }
}

function Write-Prefs([string]$BaseUrl, [string]$Key) {
  $prefs = @"
<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="base_url">$BaseUrl</string>
    <string name="device_api_key">$Key</string>
</map>
"@
  $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($prefs))
  & $Adb -s $Emu shell am force-stop $Pkg
  & $Adb -s $Emu shell "run-as $Pkg sh -c 'mkdir -p shared_prefs; echo $b64 | base64 -d > shared_prefs/eldershield.xml'" 2>$null | Out-Null
}

function Clear-RuleCache {
  & $Adb -s $Emu shell am force-stop $Pkg
  # Wipe Room DB so EmptyNoBlock path is forced
  & $Adb -s $Emu shell "run-as $Pkg sh -c 'rm -f databases/* databases/*-shm databases/*-wal files/* 2>/dev/null; true'" 2>$null | Out-Null
}

function Get-EsNotifications {
  $dump = & $Adb -s $Emu shell dumpsys notification --noredact 2>$null
  if (-not $dump) { $dump = & $Adb -s $Emu shell dumpsys notification 2>$null }
  $lines = $dump | Select-String -Pattern "pkg=$Pkg|Package=$Pkg|com\.eldershield"
  return @($lines)
}

function Invoke-InCn {
  & $Adb -s $Emu emu gsm cancel +8613999000099 2>$null | Out-Null
  & $Adb -s $Emu logcat -c
  & $Adb -s $Emu emu gsm call +8613999000099 2>$null | Out-Null
  Start-Sleep -Seconds 4
  $log = (& $Adb -s $Emu logcat -d -s ElderCallScreen:I ElderCallScreen:W | Select-Object -Last 3) -join " | "
  $scr = (& $Adb -s $Emu shell dumpsys telecom | Select-String "SCREENING_COMPLETED" | Select-Object -Last 1).Line
  & $Adb -s $Emu emu gsm cancel +8613999000099 2>$null | Out-Null
  return @{ log = "$log"; scr = "$scr" }
}

function Home-And-ScanUi {
  & $Adb -s $Emu shell input keyevent KEYCODE_HOME
  Start-Sleep -Seconds 1
  & $Adb -s $Emu shell uiautomator dump /sdcard/ui.xml 2>$null | Out-Null
  $xml = (& $Adb -s $Emu shell cat /sdcard/ui.xml 2>$null) -join ""
  return $xml
}

Write-Host "=== Fail-open / silent outage verify (AVD) ==="
Assert-Emu
& $Adb -s $Emu install -r $Apk 2>$null | Out-Null
& $Adb -s $Emu shell cmd role add-role-holder android.app.role.CALL_SCREENING $Pkg 2>$null | Out-Null
& $Adb -s $Emu shell pm grant $Pkg android.permission.READ_CONTACTS 2>$null | Out-Null
& $Adb -s $Emu shell pm grant $Pkg android.permission.READ_CALL_LOG 2>$null | Out-Null
& $Adb -s $Emu shell pm grant $Pkg android.permission.READ_PHONE_STATE 2>$null | Out-Null

# --- F0: code posture smoke via dumpsys (no Notification channel expected) ---
$pkgDump = (& $Adb -s $Emu shell dumpsys package $Pkg 2>$null) -join "`n"
if ($pkgDump -match "POST_NOTIFICATIONS") {
  Add-R "F0-notif-perm" "WARN" "POST_NOTIFICATIONS present in package dump"
} else {
  Add-R "F0-notif-perm" "PASS" "no POST_NOTIFICATIONS in package dump"
}

# --- F1: dead backend + empty cache => fail-open Allow ---
Clear-RuleCache
Write-Prefs "http://127.0.0.1:1" "test-device-key"
& $Adb -s $Emu shell am start -n "$Pkg/.ui.MainActivity" | Out-Null
Start-Sleep -Seconds 2
# Enqueue sync by tapping save if visible (admin surface only); else kick worker via activity recreate
& $Adb -s $Emu shell uiautomator dump /sdcard/ui.xml 2>$null | Out-Null
$xml = (& $Adb -s $Emu shell cat /sdcard/ui.xml 2>$null) -join ""
if ($xml -match 'id/saveProvision"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"') {
  $cx = [int](([int]$Matches[1] + [int]$Matches[3]) / 2)
  $cy = [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
  & $Adb -s $Emu shell input tap $cx $cy
}
Start-Sleep -Seconds 8
# Leave admin UI — parent path is home launcher
$homeXml = Home-And-ScanUi
$badUi = ($homeXml -match 'ElderShield|sync failed|error|차단|실패|NextDNS|Unable to|실패') -and ($homeXml -match 'com\.eldershield')
# Launcher should not show ES error dialog; package name may appear in recent apps text — require dialog-like text
$dialogish = $homeXml -match 'text="[^"]*(failed|error|Unable|실패|오류|차단됨)[^"]*"'
if ($dialogish) {
  Add-R "F1-home-dialog" "FAIL" "suspicious dialog text on home UI dump"
} else {
  Add-R "F1-home-dialog" "PASS" "no failure dialog text on home"
}

$r = Invoke-InCn
$allowed = ($r.log -match "block=false") -or ($r.scr -match "Allow") -or ($r.log -match "bundleVer=-1")
$blocked = ($r.log -match "block=true") -or ($r.scr -match "Reject")
$failOpenLog = $r.log -match "fail-open"
if ($allowed -and -not $blocked) {
  Add-R "F1-empty-cache-allow" "PASS" ("CN inbound Allow under outage. {0}" -f $r.log)
} elseif ($failOpenLog) {
  Add-R "F1-empty-cache-allow" "PASS" ("exception fail-open. {0}" -f $r.log)
} else {
  Add-R "F1-empty-cache-allow" "FAIL" ("expected Allow. log={0} scr={1}" -f $r.log, $r.scr)
}

Start-Sleep -Seconds 2
$afterNotif = Get-EsNotifications
# Active notification records for package should stay empty / unchanged for outage
$notifText = ($afterNotif | ForEach-Object { $_.Line }) -join " || "
if ($notifText -match "NotificationRecord|enqueueNotification") {
  Add-R "F1-notifications" "FAIL" $notifText.Substring(0, [Math]::Min(300, $notifText.Length))
} else {
  Add-R "F1-notifications" "PASS" ("no ES NotificationRecord; hits={0}" -f $afterNotif.Count)
}

# Toast: dumpsys window / logcat Toast
$toast = (& $Adb -s $Emu logcat -d | Select-String -Pattern "Toast|Snackbar" | Select-String -Pattern "eldershield|ElderShield" | Select-Object -Last 5)
if ($toast) {
  Add-R "F1-toast" "FAIL" ($toast -join "; ")
} else {
  Add-R "F1-toast" "PASS" "no ElderShield Toast/Snackbar in logcat"
}

# --- F2: corrupt cache => exception fail-open Allow ---
& $Adb -s $Emu shell am force-stop $Pkg
& $Adb -s $Emu shell "run-as $Pkg sh -c 'mkdir -p databases; echo CORRUPT > databases/eldershield.db'" 2>$null | Out-Null
Write-Prefs "http://127.0.0.1:1" "test-device-key"
& $Adb -s $Emu shell am start -n "$Pkg/.ui.MainActivity" | Out-Null
Start-Sleep -Seconds 2
& $Adb -s $Emu shell input keyevent KEYCODE_HOME
$r2 = Invoke-InCn
if ((($r2.log -match "block=false") -or ($r2.log -match "fail-open") -or ($r2.scr -match "Allow")) -and ($r2.log -notmatch "block=true")) {
  Add-R "F2-corrupt-failopen" "PASS" $r2.log
} else {
  Add-R "F2-corrupt-failopen" "FAIL" ("log={0} scr={1}" -f $r2.log, $r2.scr)
}

# --- F3: restore good backend + reverse; ensure still no notif spam ---
& $Adb -s $Emu reverse tcp:8765 tcp:8765 | Out-Null
Clear-RuleCache
Write-Prefs "http://127.0.0.1:8765" "test-device-key"
& $Adb -s $Emu shell am start -n "$Pkg/.ui.MainActivity" | Out-Null
Start-Sleep -Seconds 2
& $Adb -s $Emu shell uiautomator dump /sdcard/ui.xml 2>$null | Out-Null
$xml = (& $Adb -s $Emu shell cat /sdcard/ui.xml 2>$null) -join ""
if ($xml -match 'id/saveProvision"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"') {
  $cx = [int](([int]$Matches[1] + [int]$Matches[3]) / 2)
  $cy = [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
  & $Adb -s $Emu shell input tap $cx $cy
}
Start-Sleep -Seconds 12
& $Adb -s $Emu shell input keyevent KEYCODE_HOME
$r3 = Invoke-InCn
# After restore with CN call policy, may Reject — either is OK; must not notify parent
$n3 = Get-EsNotifications
$n3t = ($n3 | ForEach-Object { $_.Line }) -join " "
if ($n3t -match "NotificationRecord") {
  Add-R "F3-restore-silent" "FAIL" $n3t.Substring(0, [Math]::Min(240, $n3t.Length))
} else {
  Add-R "F3-restore-silent" "PASS" ("restored screening silent; callLog={0}" -f $r3.log)
}

$out = Join-Path $Root "docs\plans\2026-11-20-failopen-silent-results.json"
@{
  ranAt = (Get-Date).ToUniversalTime().ToString("o")
  results = $Results
  policy = @{
    emptyCacheOutage = "Allow (EmptyNoBlock)"
    staleCacheOutage = "Keep last rules (UsedCache) — no parent UI"
    exceptions = "CallResponse allow + skipNotification on reject path"
  }
} | ConvertTo-Json -Depth 6 | Set-Content $out -Encoding UTF8

Write-Host ""
Write-Host "=== Summary ==="
$Results | Group-Object status | ForEach-Object { "{0}={1}" -f $_.Name, $_.Count }
Write-Host "Wrote $out"
$fail = @($Results | Where-Object { $_.status -eq "FAIL" }).Count
exit $(if ($fail -gt 0) { 1 } else { 0 })
