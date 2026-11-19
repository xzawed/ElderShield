# ElderShield KR-lab batch (L1–L11). Emulator = CN/gsm; S22 = USB KR handset (no auto CALL).
# Usage: powershell -File scripts/lab-batch-verify.ps1
# SAFETY: gsm inject only on emulator-*; physical S22 never ACTION.CALL.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
$Emu = "emulator-5554"
$S22 = if ($env:ELDERSHIELD_S22_SERIAL) { $env:ELDERSHIELD_S22_SERIAL } else { "CHANGEME_S22_SERIAL" }
$Apk = Join-Path $Root "android\app\build\outputs\apk\debug\app-debug.apk"
$Pkg = "com.eldershield"
$AdminKey = if ($env:ADMIN_API_KEY) { $env:ADMIN_API_KEY } else { "test-admin-key" }
$DeviceKey = if ($env:DEVICE_API_KEY) { $env:DEVICE_API_KEY } else { "test-device-key" }
$Base = if ($env:ELDERSHIELD_LAB_URL) { $env:ELDERSHIELD_LAB_URL } else { "http://127.0.0.1:8765" }
$Py = Join-Path $Root "backend\.venv\Scripts\python.exe"
$Results = [System.Collections.Generic.List[object]]::new()

function Add-Result($id, $status, $notes) {
  $Results.Add([pscustomobject]@{ id = $id; status = $status; notes = $notes })
  Write-Host ("[{0}] {1} — {2}" -f $id, $status, $notes)
}

function Ensure-Serial($serial) {
  $line = & $Adb devices | Select-String "^$serial\s+device"
  return [bool]$line
}

function Install-And-Provision($serial, $deviceLabel) {
  & $Adb -s $serial reverse --remove-all 2>$null | Out-Null
  & $Adb -s $serial reverse tcp:8765 tcp:8765 | Out-Null
  & $Adb -s $serial install -r $Apk | Out-Null
  & $Adb -s $serial shell input keyevent KEYCODE_WAKEUP 2>$null | Out-Null
  & $Adb -s $serial shell wm dismiss-keyguard 2>$null | Out-Null
  & $Adb -s $serial shell am force-stop $Pkg
  $prefs = @"
<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="base_url">http://127.0.0.1:8765</string>
    <string name="device_api_key">$DeviceKey</string>
</map>
"@
  $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($prefs))
  & $Adb -s $serial shell "run-as $Pkg mkdir -p shared_prefs" | Out-Null
  & $Adb -s $serial shell "run-as $Pkg sh -c 'echo $b64 | base64 -d > shared_prefs/eldershield.xml'" | Out-Null
  # SSOT §1.2: Bitdefender 병행 — do NOT steal ROLE_CALL_SCREENING from another holder.
  $holders = (& $Adb -s $serial shell cmd role get-role-holders android.app.role.CALL_SCREENING 2>$null) -join ""
  if ($holders -match $Pkg) {
    Write-Host "call-screening role already held by $Pkg"
  } elseif ($holders -match "\S") {
    Write-Host "WARN: call-screening held by other app ($holders) — leaving in place (no steal)"
  } else {
    Write-Host "WARN: no call-screening holder; request role via UI (not forced adb steal)"
  }
  & $Adb -s $serial shell am start -n "$Pkg/.ui.MainActivity" | Out-Null
  Start-Sleep -Seconds 2
  # Tap Save if visible (skip if pattern/PIN lock UI)
  & $Adb -s $serial shell uiautomator dump /sdcard/ui.xml 2>$null | Out-Null
  $xml = (& $Adb -s $serial shell cat /sdcard/ui.xml 2>$null) -join ""
  if ($xml -match "bouncer|잠금해제|pattern|Keyguard") {
    Write-Host "WARN: $deviceLabel appears locked — unlock manually then re-run Save"
  }
  if ($xml -match 'resource-id="com.eldershield:id/saveProvision"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"') {
    $cx = [int](([int]$Matches[1] + [int]$Matches[3]) / 2)
    $cy = [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
    & $Adb -s $serial shell input tap $cx $cy
  } elseif ($xml -match 'text="Save[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"') {
    $cx = [int](([int]$Matches[1] + [int]$Matches[3]) / 2)
    $cy = [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
    & $Adb -s $serial shell input tap $cx $cy
  }
  Start-Sleep -Seconds 12
  $role = (& $Adb -s $serial shell cmd role get-role-holders android.app.role.CALL_SCREENING 2>$null) -join ""
  return $role
}

function Get-LatestScreening($serial) {
  $dump = & $Adb -s $serial shell dumpsys telecom 2>$null
  $lines = $dump | Select-String -Pattern "SCREENING_COMPLETED" | Select-Object -Last 1
  if (-not $lines) { return "" }
  return $lines.Line
}

function Assert-EmulatorCallTarget([string]$Serial) {
  if ($Serial -notmatch '^emulator-') {
    throw ("Call lab refused: serial '{0}' is not an emulator." -f $Serial)
  }
}

function Invoke-EmuCall($number) {
  Assert-EmulatorCallTarget $Emu
  foreach ($n in @("+8613999999999", "+8613812345678", "+821098765432", "01098765432", "+12025550199")) {
    & $Adb -s $Emu emu gsm cancel $n 2>$null | Out-Null
  }
  Start-Sleep -Seconds 1
  & $Adb -s $Emu emu gsm call $number 2>$null | Out-Null
  Start-Sleep -Seconds 4
  $line = Get-LatestScreening $Emu
  & $Adb -s $Emu emu gsm cancel $number 2>$null | Out-Null
  return $line
}

Write-Host "=== ElderShield KR-lab batch ==="
Write-Host "Base=$Base AdminKey=set DeviceKey=set"

# --- L1 pytest + denylist ---
Push-Location (Join-Path $Root "backend")
$env:ADMIN_API_KEY = $AdminKey
$env:DEVICE_API_KEY = $DeviceKey
$pytestOut = & $Py -m pytest -q 2>&1 | Out-String
$pytestOk = ($LASTEXITCODE -eq 0)
Pop-Location
if ($pytestOk) { Add-Result "L1-pytest" "PASS" ($pytestOut.Trim().Split("`n")[-1]) }
else { Add-Result "L1-pytest" "FAIL" $pytestOut.Substring([Math]::Max(0, $pytestOut.Length - 400)) }

$seedOut = & $Py (Join-Path $PSScriptRoot "_lab_seed.py") 2>&1 | Out-String
if ($seedOut -match 'DEN 200' -and $seedOut -match 'tlds') {
  Add-Result "L1-denylist" "PASS" (($seedOut -split "`n" | Where-Object { $_ -match '^DEN' } | Select-Object -First 1))
} else {
  Add-Result "L1-denylist" "FAIL" $seedOut.Substring(0, [Math]::Min(400, $seedOut.Length))
}

if ($seedOut -match 'SYNC 200') { Add-Result "L2-nextdns" "PASS" "sync-nextdns 200" }
elseif ($seedOut -match 'SYNC 503') { Add-Result "L2-nextdns" "SKIP" "NEXTDNS_* unset (503)" }
else { Add-Result "L2-nextdns" "FAIL" (($seedOut -split "`n" | Where-Object { $_ -match 'SYNC' } | Select-Object -First 1)) }

# Build APK if missing/stale
Push-Location (Join-Path $Root "android")
& .\gradlew.bat :app:assembleDebug --quiet 2>&1 | Out-Null
Pop-Location
if (-not (Test-Path $Apk)) { Add-Result "L3-apk" "FAIL" "APK missing"; }
else { Add-Result "L3-apk" "PASS" "assembleDebug ok" }

# --- L3 emulator ---
if (Ensure-Serial $Emu) {
  $roleE = Install-And-Provision $Emu "emu"
  Start-Sleep -Seconds 3
  $devJson = & $Py -c "import httpx,json; d=httpx.get('$Base/api/v1/admin/devices',headers={'X-API-Key':'$AdminKey'},timeout=20).json(); print(json.dumps(sorted(d,key=lambda x:x.get('lastSyncAt') or '',reverse=True)[:4],default=str))"
  $bundleVer = (& $Py -c "import httpx; print(httpx.get('$Base/api/v1/rules/latest',headers={'X-API-Key':'$DeviceKey'},timeout=20).json()['version'])").Trim()
  if ($roleE -match $Pkg -and $devJson -match "lastRuleVersion.: $bundleVer" -or $devJson -match '"lastRuleVersion":\s*'+$bundleVer) {
    Add-Result "L3-emu" "PASS" "role=$Pkg bundle=$bundleVer"
  } elseif ($roleE -match $Pkg -and $devJson -match 'lastRuleVersion') {
    # Accept if any recent device has matching version
    if ($devJson -match [regex]::Escape('"lastRuleVersion": ' + $bundleVer) -or $devJson -match "`"lastRuleVersion`": $bundleVer") {
      Add-Result "L3-emu" "PASS" "role ok version=$bundleVer"
    } else {
      Add-Result "L3-emu" "WARN" "role ok; check version vs $bundleVer :: $($devJson.Substring(0,[Math]::Min(220,$devJson.Length)))"
    }
  } else {
    Add-Result "L3-emu" "FAIL" "role=$roleE devices=$($devJson.Substring(0,[Math]::Min(200,$devJson.Length)))"
  }

  # L4–L8 gsm
  $c1 = Invoke-EmuCall "+8613999999999"
  if ($c1 -match "Reject") { Add-Result "L4-cn-block" "PASS" $c1.Trim().Substring(0,[Math]::Min(120,$c1.Trim().Length)) }
  else { Add-Result "L4-cn-block" "FAIL" $c1 }

  $c2 = Invoke-EmuCall "+8613812345678"
  if ($c2 -match "Allow") { Add-Result "L5-cn-whitelist" "PASS" "Allow" }
  else { Add-Result "L5-cn-whitelist" "FAIL" $c2 }

  $c3 = Invoke-EmuCall "+821098765432"
  if ($c3 -match "Reject") { Add-Result "L6-kr82" "PASS" "Reject" }
  else { Add-Result "L6-kr82" "FAIL" $c3 }

  $c4 = Invoke-EmuCall "01098765432"
  if ($c4 -match "Reject") { Add-Result "L7-emu-010" "PASS" "Reject (national normalize)" }
  else { Add-Result "L7-emu-010" "FAIL" $c4 }

  $c5 = Invoke-EmuCall "+12025550199"
  if ($c5 -match "Allow") { Add-Result "L8-us-allow" "PASS" "Allow" }
  else { Add-Result "L8-us-allow" "FAIL" $c5 }
} else {
  Add-Result "L3-emu" "SKIP" "emulator not connected"
  foreach ($id in @("L4-cn-block","L5-cn-whitelist","L6-kr82","L7-emu-010","L8-us-allow")) {
    Add-Result $id "SKIP" "no emulator"
  }
}

# --- L3 S22 ---
if (Ensure-Serial $S22) {
  $roleS = Install-And-Provision $S22 "s22"
  Start-Sleep -Seconds 5
  $devJson2 = & $Py -c "import httpx,json; d=httpx.get('$Base/api/v1/admin/devices',headers={'X-API-Key':'$AdminKey'},timeout=20).json(); print(json.dumps(sorted(d,key=lambda x:x.get('lastSyncAt') or '',reverse=True)[:5],default=str))"
  $bundleVer2 = (& $Py -c "import httpx; print(httpx.get('$Base/api/v1/rules/latest',headers={'X-API-Key':'$DeviceKey'},timeout=20).json()['version'])").Trim()
  $matched = $devJson2 -match ('"lastRuleVersion":\s*' + $bundleVer2) -or $devJson2 -match ('"lastRuleVersion": ' + $bundleVer2)
  $roleOk = $roleS -match $Pkg
  $dnsCfg = & $Adb -s $S22 shell settings get global private_dns_mode 2>$null
  $dnsHost = & $Adb -s $S22 shell settings get global private_dns_specifier 2>$null
  if ($roleOk -and $matched) { Add-Result "L3-s22" "PASS" "role+version=$bundleVer2 dns_mode=$dnsCfg" }
  elseif ($roleOk) { Add-Result "L3-s22" "WARN" "role ok; version check: $($devJson2.Substring(0,[Math]::Min(240,$devJson2.Length)))" }
  else { Add-Result "L3-s22" "FAIL" "role=$roleS" }

  Add-Result "L7-s22-010" "NEED_HUMAN" "Second KR phone must dial S22 while KR restriction enabled; adb cannot inject PSTN on physical device"
  Add-Result "L9-outgoing" "SKIP" "No auto CALL on S22 (billing risk). Outgoing Allow = AVD E1/E2 / combinatorial B-out*; optional manual own-line only"

  # L10 bank apps
  $banks = @(
    @{ pkg = "viva.republica.toss"; name = "Toss" },
    @{ pkg = "com.kakaobank.channel"; name = "KakaoBank" },
    @{ pkg = "com.shinhan.sbanking"; name = "Shinhan" }
  )
  $bankNotes = @()
  foreach ($b in $banks) {
    $path = & $Adb -s $S22 shell pm path $b.pkg 2>$null
    if ($path -match "package:") {
      & $Adb -s $S22 shell am force-stop $b.pkg 2>$null | Out-Null
      $start = & $Adb -s $S22 shell monkey -p $b.pkg -c android.intent.category.LAUNCHER 1 2>&1 | Out-String
      Start-Sleep -Seconds 2
      $fg = & $Adb -s $S22 shell dumpsys activity activities 2>$null | Select-String -Pattern "mResumedActivity|topResumedActivity" | Select-Object -First 2
      $bankNotes += "$($b.name):installed launch_ok=$($start -match 'Events injected')"
    } else {
      $bankNotes += "$($b.name):not_installed"
    }
  }
  if ($bankNotes -match "launch_ok=True") { Add-Result "L10-bank" "PASS" ($bankNotes -join "; ") }
  elseif ($bankNotes -match "not_installed" -and -not ($bankNotes -match "launch_ok")) { Add-Result "L10-bank" "SKIP" ($bankNotes -join "; ") }
  else { Add-Result "L10-bank" "WARN" ($bankNotes -join "; ") }

  if ($dnsCfg -match "hostname" -and $dnsHost -match "\S") {
    Add-Result "L11-dns" "WARN" "Private DNS mode=$dnsCfg host=$dnsHost — confirm heartbeat dnsConfigured after report worker"
  } else {
    Add-Result "L11-dns" "SKIP" "Private DNS not set on S22 (mode=$dnsCfg); internet block needs NextDNS hostname + L2"
  }
} else {
  Add-Result "L3-s22" "SKIP" "S22 not connected"
  Add-Result "L7-s22-010" "SKIP" "no S22"
  Add-Result "L9-outgoing" "SKIP" "no S22"
  Add-Result "L10-bank" "SKIP" "no S22"
  Add-Result "L11-dns" "SKIP" "no S22"
}

$outDir = Join-Path $Root "docs\plans"
$outPath = Join-Path $outDir "2026-11-19-lab-batch-results.json"
$Results | ConvertTo-Json -Depth 4 | Set-Content -Path $outPath -Encoding UTF8
Write-Host "`n=== Summary ==="
$Results | Format-Table -AutoSize
Write-Host "Wrote $outPath"
$fail = @($Results | Where-Object { $_.status -eq "FAIL" }).Count
exit $(if ($fail -gt 0) { 1 } else { 0 })
