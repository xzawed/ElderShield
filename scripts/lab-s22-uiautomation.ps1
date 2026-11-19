# S22 USB + UIAutomator substitute for operator device checks (L3/L10/L11).
# Call place/answer on physical SIMs is NOT automated (billing / wrong-number risk).
# L7/L9 call proof = emulator gsm / ACTION.CALL on AVD only. See device-test.md §8 safety.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
$S22 = "CHANGEME_S22_SERIAL"
$Emu = "emulator-5554"
$Pkg = "com.eldershield"
$Apk = Join-Path $Root "android\app\build\outputs\apk\debug\app-debug.apk"
$Py = Join-Path $Root "backend\.venv\Scripts\python.exe"
$Base = "http://127.0.0.1:8765"
$AdminKey = "test-admin-key"
$DeviceKey = "test-device-key"
$Results = [System.Collections.Generic.List[object]]::new()

function Assert-EmulatorForPlaceCall {
  param([string]$Serial, [string]$Action)
  if ($Serial -notmatch '^emulator-') {
    throw ("Refused '{0}' on physical serial {1}. Use AVD only." -f $Action, $Serial)
  }
}

function Add-R($id, $status, $notes) {
  $Results.Add([pscustomobject]@{ id = $id; status = $status; notes = $notes })
  Write-Host ("[{0}] {1} — {2}" -f $id, $status, $notes)
}

function Ensure-Device($serial) {
  return [bool](& $Adb devices | Select-String "^$serial\s+device")
}

function Dump-Ui($serial) {
  & $Adb -s $serial shell uiautomator dump /sdcard/ui.xml 2>$null | Out-Null
  return ((& $Adb -s $serial shell cat /sdcard/ui.xml 2>$null) -join "")
}

function Tap-Match($serial, $regex) {
  $xml = Dump-Ui $serial
  if ($xml -match $regex) {
    $cx = [int](([int]$Matches[1] + [int]$Matches[3]) / 2)
    $cy = [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
    & $Adb -s $serial shell input tap $cx $cy
    return $true
  }
  return $false
}

function Dismiss-Permissions($serial) {
  for ($i = 0; $i -lt 4; $i++) {
    $xml = Dump-Ui $serial
    if ($xml -match 'permission_allow_button"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"') {
      $cx = [int](([int]$Matches[1] + [int]$Matches[3]) / 2)
      $cy = [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
      & $Adb -s $serial shell input tap $cx $cy
      Start-Sleep -Seconds 1
      continue
    }
    if ($xml -match 'text="(?:Allow|허용|While using the app|앱 사용 중에만 허용)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"') {
      $cx = [int](([int]$Matches[1] + [int]$Matches[3]) / 2)
      $cy = [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
      & $Adb -s $serial shell input tap $cx $cy
      Start-Sleep -Seconds 1
      continue
    }
    break
  }
}

function Try-Unlock($serial) {
  & $Adb -s $serial shell input keyevent KEYCODE_WAKEUP
  Start-Sleep -Milliseconds 400
  & $Adb -s $serial shell wm dismiss-keyguard 2>$null | Out-Null
  & $Adb -s $serial shell input keyevent 82
  Start-Sleep -Milliseconds 400
  & $Adb -s $serial shell input swipe 720 2400 720 800 300
  Start-Sleep -Seconds 1
  $xml = Dump-Ui $serial
  if ($xml -match "bouncer|잠금해제|pattern|Keyguard|PIN") {
    return $false
  }
  return $true
}

Write-Host "=== S22 UIAutomator substitute lab ==="
if (-not (Ensure-Device $S22)) { throw "S22 $S22 not connected" }

# Build if needed
if (-not (Test-Path $Apk)) {
  Push-Location (Join-Path $Root "android")
  & .\gradlew.bat :app:assembleDebug --quiet
  Pop-Location
}

& $Adb -s $S22 reverse tcp:8765 tcp:8765 | Out-Null
& $Adb -s $S22 install -r $Apk | Out-Null
& $Adb -s $S22 shell pm grant $Pkg android.permission.READ_CONTACTS 2>$null
& $Adb -s $S22 shell pm grant $Pkg android.permission.READ_CALL_LOG 2>$null
& $Adb -s $S22 shell pm grant $Pkg android.permission.READ_PHONE_STATE 2>$null

$unlocked = Try-Unlock $S22
if (-not $unlocked) {
  Add-R "U0-unlock" "WARN" "Pattern/PIN lock — continuing with adb-capable steps only"
} else {
  Add-R "U0-unlock" "PASS" "Keyguard dismissed or not present"
}

# Provision prefs (works even if locked)
$prefs = @"
<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="base_url">http://127.0.0.1:8765</string>
    <string name="device_api_key">$DeviceKey</string>
</map>
"@
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($prefs))
& $Adb -s $S22 shell am force-stop $Pkg
& $Adb -s $S22 shell "run-as $Pkg mkdir -p shared_prefs" | Out-Null
& $Adb -s $S22 shell "run-as $Pkg sh -c 'echo $b64 | base64 -d > shared_prefs/eldershield.xml'" | Out-Null

# Role: do NOT steal from peers (§1.2.1). Report only.
$holders = (& $Adb -s $S22 shell cmd role get-role-holders android.app.role.CALL_SCREENING 2>$null) -join ""
$default = (& $Adb -s $S22 shell dumpsys telecom | Select-String "DefaultCallScreeningApp" | Select-Object -First 1).Line
Add-R "U1-role" $(if ($holders -match $Pkg) { "PASS" } else { "WARN" }) "holders=$holders; $default"

& $Adb -s $S22 shell am start -n "$Pkg/.ui.MainActivity" | Out-Null
Start-Sleep -Seconds 2
Dismiss-Permissions $S22
$saved = Tap-Match $S22 'id/saveProvision"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
if (-not $saved) {
  $saved = Tap-Match $S22 'text="Save[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
}
Start-Sleep -Seconds 14

$devJson = & $Py -c "import httpx,json; print(json.dumps(httpx.get('$Base/api/v1/admin/devices',headers={'X-API-Key':'$AdminKey'},timeout=20).json(),default=str))"
$bundleVer = (& $Py -c "import httpx; print(httpx.get('$Base/api/v1/rules/latest',headers={'X-API-Key':'$DeviceKey'},timeout=20).json()['version'])").Trim()
if ($devJson -match '"lastRuleVersion":\s*' + [regex]::Escape($bundleVer) -or $devJson -match '"lastRuleVersion": ' + $bundleVer) {
  Add-R "U2-sync" "PASS" "bundle=$bundleVer seen in devices"
} elseif ($devJson -match "lastSyncAt") {
  Add-R "U2-sync" "WARN" "heartbeat present; check version vs $bundleVer (save tapped=$saved)"
} else {
  Add-R "U2-sync" "FAIL" "no devices heartbeat"
}

# L11 substitute: set trusted Private DNS via settings (no NextDNS API keys required for dnsConfigured path)
$prevMode = (& $Adb -s $S22 shell settings get global private_dns_mode).Trim()
$prevSpec = (& $Adb -s $S22 shell settings get global private_dns_specifier).Trim()
& $Adb -s $S22 shell settings put global private_dns_mode hostname
& $Adb -s $S22 shell settings put global private_dns_specifier "dns.nextdns.io"
$modeNow = (& $Adb -s $S22 shell settings get global private_dns_mode).Trim()
$specNow = (& $Adb -s $S22 shell settings get global private_dns_specifier).Trim()
if ($modeNow -eq "hostname" -and $specNow -match "nextdns") {
  Add-R "U3-dns-settings" "PASS" "mode=$modeNow specifier=$specNow (prev=$prevMode/$prevSpec)"
} else {
  Add-R "U3-dns-settings" "FAIL" "mode=$modeNow spec=$specNow"
}

# Re-enqueue DeviceReportWorker after DNS change (Save may be blocked by lock)
& $Adb -s $S22 shell am force-stop $Pkg
& $Adb -s $S22 shell am start -n "$Pkg/.ui.MainActivity" | Out-Null
Start-Sleep -Seconds 2
Dismiss-Permissions $S22
Tap-Match $S22 'id/saveProvision"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"' | Out-Null
Start-Sleep -Seconds 16

$afterDns = & $Py -c @"
import httpx, json
d=httpx.get('$Base/api/v1/admin/devices',headers={'X-API-Key':'$AdminKey'},timeout=20).json()
rows=sorted(d,key=lambda z:z.get('lastSyncAt') or '', reverse=True)[:5]
print(json.dumps([{k:x.get(k) for k in ['deviceUuid','dnsConfigured','callScreeningEnabled','callScreeningHeldBy','callScreeningPeers','lastRuleVersion','lastSyncAt']} for x in rows], default=str))
"@
if ($afterDns -match '"dnsConfigured":\s*true') {
  Add-R "U4-dnsConfigured" "PASS" "heartbeat dnsConfigured=true"
} else {
  Add-R "U4-dnsConfigured" "WARN" "dnsConfigured not yet true — $afterDns".Substring(0, [Math]::Min(280, $afterDns.Length))
}

# L9 outgoing on S22: never ACTION.CALL (PSTN). DIAL opens dialer UI only.
# Canonical outgoing Allow proof = AVD E1/E2 / combinatorial B-out*.
& $Adb -s $S22 shell am start -a android.intent.action.DIAL -d tel:114 2>&1 | Out-Null
Start-Sleep -Seconds 2
$dialFg = & $Adb -s $S22 shell dumpsys activity activities 2>$null |
  Select-String -Pattern "mResumedActivity|topResumedActivity" | Select-Object -First 2
& $Adb -s $S22 shell input keyevent KEYCODE_BACK 2>$null | Out-Null
Add-R "U5-outgoing" "SKIP" ("no auto CALL on physical device; DIAL-only. Outgoing Allow = AVD. dialer=$($dialFg -join '; ')")

# L10 banks via monkey
$bankNotes = @()
foreach ($b in @(
  @{ pkg = "viva.republica.toss"; name = "Toss" },
  @{ pkg = "com.kakaobank.channel"; name = "KakaoBank" },
  @{ pkg = "com.shinhan.sbanking"; name = "Shinhan" }
)) {
  $path = & $Adb -s $S22 shell pm path $b.pkg 2>$null
  if ($path -match "package:") {
    & $Adb -s $S22 shell am force-stop $b.pkg 2>$null | Out-Null
    $out = & $Adb -s $S22 shell monkey -p $b.pkg -c android.intent.category.LAUNCHER 1 2>&1 | Out-String
    Start-Sleep -Seconds 2
    $bankNotes += "$($b.name):ok=$($out -match 'Events injected')"
  } else {
    $bankNotes += "$($b.name):not_installed"
  }
}
if ($bankNotes -match "ok=True") { Add-R "U6-bank" "PASS" ($bankNotes -join "; ") }
else { Add-R "U6-bank" "SKIP" ($bankNotes -join "; ") }

# L2 NextDNS API — still needs secrets
$sync = & $Py -c "import httpx; r=httpx.post('$Base/api/v1/admin/dns-denylist/sync-nextdns',headers={'X-API-Key':'$AdminKey'},timeout=20); print(r.status_code, r.text[:200])"
if ($sync -match "^200") { Add-R "U7-nextdns-api" "PASS" $sync }
elseif ($sync -match "503") { Add-R "U7-nextdns-api" "SKIP" "NEXTDNS_* unset — DNS path verified via settings only" }
else { Add-R "U7-nextdns-api" "FAIL" $sync }

# L7 substitute: physical inject impossible — re-confirm on emulator if up
if (Ensure-Device $Emu) {
  Assert-EmulatorForPlaceCall -Serial $Emu -Action "emu gsm call"
  & $Adb -s $Emu emu gsm cancel 01098765432 2>$null | Out-Null
  # Ensure KR enabled briefly for substitute proof, then leave as-is if already disabled policy
  & $Py -c @"
import httpx
h={'X-API-Key':'$AdminKey'}
rows=httpx.get('$Base/api/v1/admin/country-restrictions',headers=h,timeout=20).json()
kr=next((r for r in rows if r.get('countries')==['KR']), None)
if kr:
  httpx.put(f\"$Base/api/v1/admin/country-restrictions/{kr['id']}\",headers=h,json={
    'name':kr['name'],'countries':['KR'],'applyTo':['call'],'enabled':True,'description':'uiauto substitute re-enable'
  },timeout=20)
"@
  Start-Sleep -Seconds 1
  & $Adb -s $Emu reverse tcp:8765 tcp:8765 | Out-Null
  # Force emu sync if possible
  & $Adb -s $Emu shell am start -n "$Pkg/.ui.MainActivity" 2>$null | Out-Null
  Start-Sleep -Seconds 2
  Tap-Match $Emu 'id/saveProvision"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"' | Out-Null
  Start-Sleep -Seconds 10
  & $Adb -s $Emu emu gsm call 01098765432 2>$null | Out-Null
  Start-Sleep -Seconds 4
  $line = (& $Adb -s $Emu shell dumpsys telecom | Select-String "SCREENING_COMPLETED" | Select-Object -Last 1).Line
  & $Adb -s $Emu emu gsm cancel 01098765432 2>$null | Out-Null
  if ($line -match "Reject") { Add-R "U8-l7-emu-sub" "PASS" "010 Reject on emulator (physical PSTN inject N/A)" }
  else { Add-R "U8-l7-emu-sub" "WARN" $line }
  # Re-disable KR lab rule
  & $Py -c @"
import httpx
h={'X-API-Key':'$AdminKey'}
rows=httpx.get('$Base/api/v1/admin/country-restrictions',headers=h,timeout=20).json()
kr=next((r for r in rows if r.get('countries')==['KR']), None)
if kr:
  httpx.put(f\"$Base/api/v1/admin/country-restrictions/{kr['id']}\",headers=h,json={
    'name':kr['name'],'countries':['KR'],'applyTo':['call'],'enabled':False,'description':'lab cleanup after uiauto'
  },timeout=20)
  print('KR disabled')
"@
} else {
  Add-R "U8-l7-emu-sub" "SKIP" "emulator not connected"
}

# Optional: restore previous DNS mode (keep hostname if was unset — leave trusted for lab)
# Restore previous to avoid surprising the operator network path
& $Adb -s $S22 shell settings put global private_dns_mode $prevMode
if ($prevSpec -and $prevSpec -ne "null") {
  & $Adb -s $S22 shell settings put global private_dns_specifier $prevSpec
} else {
  & $Adb -s $S22 shell settings delete global private_dns_specifier 2>$null | Out-Null
}
Add-R "U9-dns-restore" "PASS" "restored mode=$prevMode spec=$prevSpec"

$outPath = Join-Path $Root "docs\plans\2026-11-19-lab-s22-uiauto-results.json"
$Results | ConvertTo-Json -Depth 4 | Set-Content -Path $outPath -Encoding UTF8
Write-Host "`n=== Summary ==="
$Results | Format-Table -AutoSize
Write-Host "Wrote $outPath"
$fail = @($Results | Where-Object { $_.status -eq "FAIL" }).Count
exit $(if ($fail -gt 0) { 1 } else { 0 })
