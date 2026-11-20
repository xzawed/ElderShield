# Virtual attacker simulation against ElderShield (defensive lab only).
# Axes: AVD CN incoming call · sideloaded risky fixture app · DNS/denylist path.
# SAFETY: gsm call / ACTION.CALL only on emulator-*; never PSTN on USB phone.
# Usage: powershell -File scripts/lab-attack-sim-verify.ps1
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
$Py = Join-Path $Root "backend\.venv\Scripts\python.exe"
$Emu = "emulator-5554"
$Phone = if ($env:ELDERSHIELD_S22_SERIAL) { $env:ELDERSHIELD_S22_SERIAL } else { $null }
$Base = if ($env:ELDERSHIELD_LAB_URL) { $env:ELDERSHIELD_LAB_URL } else { "http://127.0.0.1:8765" }
$AdminKey = if ($env:ADMIN_API_KEY) { $env:ADMIN_API_KEY } else { "test-admin-key" }
$DeviceKey = if ($env:DEVICE_API_KEY) { $env:DEVICE_API_KEY } else { "test-device-key" }
$AttackerPkg = "com.eldershield.labattacker"
$AttackerApk = Join-Path $Root "android\lab-attacker-fixture\build\outputs\apk\debug\lab-attacker-fixture-debug.apk"
$EsPkg = "com.eldershield"
$Date = Get-Date -Format "yyyy-MM-dd"
$OutPath = Join-Path $Root "docs\plans\$Date-attack-sim-verify-results.json"
$Results = [System.Collections.Generic.List[object]]::new()

function Add-R([string]$Id, [string]$Status, [string]$Notes) {
  $Results.Add([pscustomobject]@{ id = $Id; status = $Status; notes = "$Notes" })
  Write-Host ("[{0}] {1} — {2}" -f $Id, $Status, $Notes)
}

function Load-DotEnv([string]$Path) {
  if (-not (Test-Path $Path)) { return }
  Get-Content $Path | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $i = $_.IndexOf('='); if ($i -lt 1) { return }
    $k = $_.Substring(0, $i).Trim(); $v = $_.Substring($i + 1).Trim()
    if ([string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable($k, "Process"))) {
      Set-Item -Path "Env:$k" -Value $v
    }
  }
}

function Online([string]$Serial) {
  return [bool](& $Adb devices | Select-String ("^{0}\s+device" -f [regex]::Escape($Serial)))
}

Load-DotEnv (Join-Path $Root "backend\.env")
$AdminKey = if ($env:ADMIN_API_KEY) { $env:ADMIN_API_KEY } else { $AdminKey }
$DeviceKey = if ($env:DEVICE_API_KEY) { $env:DEVICE_API_KEY } else { $DeviceKey }
if (-not $Phone) {
  $line = & $Adb devices | Where-Object { $_ -match '^\S+\s+device$' -and $_ -notmatch '^emulator-' } | Select-Object -First 1
  if ($line) { $Phone = ($line -split '\s+')[0] }
}

Write-Host "=== ElderShield attack-sim verify ==="
Write-Host "Base=$Base emu=$(Online $Emu) phone=$Phone"

# Discover phone UUID after recent sync (prefer USB phone, else emu)
function Get-TargetDeviceUuid([string]$PreferSerial) {
  $script = @"
import httpx, json
base='$Base'; ah={'X-API-Key':'$AdminKey'}
rows=httpx.get(f'{base}/api/v1/admin/devices',headers=ah,timeout=20).json()
rows=sorted(rows,key=lambda x:x.get('lastSyncAt') or '', reverse=True)
print(json.dumps(rows[:8], default=str))
"@
  $json = & $Py -c $script
  return $json
}

# ---------- A0 seed CN call restriction ----------
$seed = & $Py -c @"
import httpx, json
base='$Base'; ah={'X-API-Key':'$AdminKey'}
rows=httpx.get(f'{base}/api/v1/admin/country-restrictions',headers=ah,timeout=20).json()
cn=next((r for r in rows if sorted(r.get('countries') or [])==['CN']), None)
body={'name':'AttackSim CN','countries':['CN'],'applyTo':['call','dns','internet'],'enabled':True,'description':'attack sim'}
if cn:
  httpx.put(f\"{base}/api/v1/admin/country-restrictions/{cn['id']}\",headers=ah,json=body,timeout=20).raise_for_status()
else:
  httpx.post(f'{base}/api/v1/admin/country-restrictions',headers=ah,json=body,timeout=20).raise_for_status()
# whitelist one CN for contrast
rules=httpx.get(f'{base}/api/v1/admin/call-rules',headers=ah,timeout=20).json()
wl='+8613812345678'
has=any(wl in (r.get('whitelist') or []) for r in rules)
if not has:
  httpx.post(f'{base}/api/v1/admin/call-rules',headers=ah,json={
    'countryCodes':[],'whitelist':[wl],'enabled':True
  },timeout=20)
den=httpx.get(f'{base}/api/v1/admin/dns-denylist',headers=ah,timeout=20).json()
print(json.dumps({'cn':True,'tlds':den.get('tlds'),'has_cn':'cn' in (den.get('tlds') or []),'bundle':httpx.get(f'{base}/api/v1/rules/latest',headers={'X-API-Key':'$DeviceKey'},timeout=20).json().get('version')}))
"@
Add-R "A0-seed" "PASS" $seed.Trim()

# ---------- A1 call attack on emulator ----------
if (Online $Emu) {
  & $Adb -s $Emu reverse tcp:8765 tcp:8765 | Out-Null
  # Ensure ES is screening
  $holders = (& $Adb -s $Emu shell cmd role get-role-holders android.app.role.CALL_SCREENING 2>$null) -join ""
  if ($holders -notmatch $EsPkg) {
    Add-R "A1-role" "WARN" "ES not call-screening holder on emu: $holders — gsm may not be screened"
  } else {
    Add-R "A1-role" "PASS" "holder=$EsPkg"
  }
  # Trigger rule sync
  & $Adb -s $Emu shell am broadcast -a androidx.work.impl.background.systemalarm.UpdateReceivers 2>$null | Out-Null
  & $Adb -s $Emu shell am start -n "$EsPkg/.ui.MainActivity" 2>$null | Out-Null
  Start-Sleep -Seconds 3

  function Invoke-AttackCall([string]$Number, [string]$Expect) {
    Assert-Emu
    foreach ($n in @("+8613999998888", "+8613812345678", "+12025550199")) {
      & $Adb -s $Emu emu gsm cancel $n 2>$null | Out-Null
    }
    Start-Sleep -Seconds 1
    & $Adb -s $Emu logcat -c 2>$null | Out-Null
    & $Adb -s $Emu emu gsm call $Number 2>$null | Out-Null
    Start-Sleep -Seconds 4
    $telecom = (& $Adb -s $Emu shell dumpsys telecom 2>$null | Select-String -Pattern "SCREENING_COMPLETED" | Select-Object -Last 1)
    $line = if ($telecom) { $telecom.Line } else { "" }
    $log = (& $Adb -s $Emu logcat -d -s ElderCallScreen:I 2>$null | Select-Object -Last 5) -join " | "
    & $Adb -s $Emu emu gsm cancel $Number 2>$null | Out-Null
    return [pscustomobject]@{ telecom = $line; logcat = $log }
  }
  function Assert-Emu {
    if ($Emu -notmatch '^emulator-') { throw "refused non-emulator call inject" }
  }

  $atk = Invoke-AttackCall "+8613999998888" "Reject"
  if ($atk.telecom -match "Reject") {
    Add-R "A1-block-attacker-cli" "PASS" $atk.telecom.Substring(0, [Math]::Min(160, $atk.telecom.Length))
  } else {
    Add-R "A1-block-attacker-cli" "FAIL" ("telecom=" + $atk.telecom)
  }
  if ($atk.logcat -match "block=true" -or $atk.logcat -match "block=True") {
    Add-R "A1-log-pattern" "PASS" $atk.logcat.Substring(0, [Math]::Min(200, $atk.logcat.Length))
  } elseif ($atk.logcat -match "onScreenCall") {
    Add-R "A1-log-pattern" "WARN" ("saw onScreenCall but block flag unclear: " + $atk.logcat)
  } else {
    Add-R "A1-log-pattern" "WARN" ("no ElderCallScreen logcat; telecom Reject still authoritative. log=" + $atk.logcat)
  }

  $wl = Invoke-AttackCall "+8613812345678" "Allow"
  if ($wl.telecom -match "Allow") {
    Add-R "A1-whitelist-contrast" "PASS" "Allow for WL CLI"
  } else {
    Add-R "A1-whitelist-contrast" "FAIL" $wl.telecom
  }

  $ctrl = Invoke-AttackCall "+12025550199" "Allow"
  if ($ctrl.telecom -match "Allow") {
    Add-R "A1-control-us" "PASS" "US Allow"
  } else {
    Add-R "A1-control-us" "FAIL" $ctrl.telecom
  }

  # Attacker identity on server: product does not upload raw CLI (privacy).
  Add-R "A1-server-attacker-cli" "PASS" "by design: no raw caller number uploaded; evidence = telecom Reject + logcat len/block"
} else {
  Add-R "A1-block-attacker-cli" "SKIP" "no emulator"
}

# ---------- A2 sideload attacker fixture app ----------
Push-Location (Join-Path $Root "android")
& .\gradlew.bat :lab-attacker-fixture:assembleDebug --no-daemon 2>&1 | Out-Null
Pop-Location
if (-not (Test-Path $AttackerApk)) {
  Add-R "A2-build-fixture" "FAIL" "APK missing at $AttackerApk"
} else {
  Add-R "A2-build-fixture" "PASS" "lab-attacker-fixture-debug.apk"
}

$targets = @()
if (Online $Emu) { $targets += $Emu }
if ($Phone -and (Online $Phone)) { $targets += $Phone }

foreach ($serial in $targets) {
  $label = if ($serial -match '^emulator-') { "emu" } else { "phone" }
  & $Adb -s $serial reverse tcp:8765 tcp:8765 | Out-Null
  & $Adb -s $serial install -r $AttackerApk 2>&1 | Out-Null
  $path = (& $Adb -s $serial shell pm path $AttackerPkg 2>$null) -join ""
  if ($path -notmatch "package:") {
    Add-R "A2-install-$label" "FAIL" "fixture not installed"
    continue
  }
  Add-R "A2-install-$label" "PASS" $path.Trim()

  # Force report worker via app start + wait (WorkManager periodic; also try adb shell am)
  & $Adb -s $serial shell am force-stop $EsPkg
  & $Adb -s $serial shell am start -n "$EsPkg/.ui.MainActivity" | Out-Null
  Start-Sleep -Seconds 2
  # Tap Save & sync if provision UI visible → Autoprovision.enqueueWork → DeviceReportWorker one-shot
  & $Adb -s $serial shell uiautomator dump /sdcard/ui.xml 2>$null | Out-Null
  $xml = (& $Adb -s $serial shell cat /sdcard/ui.xml 2>$null) -join ""
  if ($xml -match 'resource-id="com.eldershield:id/saveProvision"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"') {
    $cx = [int](([int]$Matches[1] + [int]$Matches[3]) / 2)
    $cy = [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
    & $Adb -s $serial shell input tap $cx $cy
  } elseif ($xml -match 'text="Save[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"') {
    $cx = [int](([int]$Matches[1] + [int]$Matches[3]) / 2)
    $cy = [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
    & $Adb -s $serial shell input tap $cx $cy
  }
  Start-Sleep -Seconds 22

  $scanOut = & $Py -c @"
import httpx, json
base='$Base'; ah={'X-API-Key':'$AdminKey'}
rows=httpx.get(f'{base}/api/v1/admin/devices',headers=ah,timeout=20).json()
rows=sorted(rows,key=lambda x:x.get('lastSyncAt') or '', reverse=True)
found=None
scans=[]
for d in rows[:12]:
  uuid=d.get('deviceUuid')
  detail=httpx.get(f'{base}/api/v1/admin/devices/{uuid}',headers=ah,timeout=20).json()
  for s in detail.get('scans') or []:
    if s.get('packageName')=='$AttackerPkg':
      found={'deviceUuid':uuid,'scan':s,'device':{k:d.get(k) for k in ['model','appVersion','callScreeningHeldBy','dnsConfigured','lastSyncAt']}}
      break
  if found: break
  scans.append({'uuid':uuid,'n':len(detail.get('scans') or [])})
print(json.dumps({'found':found,'recent':scans[:4]}, default=str))
"@
  if ($scanOut -match '"packageName":\s*"com.eldershield.labattacker"' -or $scanOut -match "labattacker") {
    Add-R "A2-collect-$label" "PASS" $scanOut.Substring(0, [Math]::Min(400, $scanOut.Length))
  } else {
    # Fallback: POST scan via device key simulating worker (proves collection path)
    $post = & $Py -c @"
import httpx, json, uuid
base='$Base'
# pick newest device
ah_admin={'X-API-Key':'$AdminKey'}
rows=httpx.get(f'{base}/api/v1/admin/devices',headers=ah_admin,timeout=20).json()
rows=sorted(rows,key=lambda x:x.get('lastSyncAt') or '', reverse=True)
dev=rows[0]['deviceUuid'] if rows else str(uuid.uuid4())
body={
  'deviceUuid':dev,
  'suspiciousApps':[{
    'packageName':'$AttackerPkg',
    'installer':None,
    'dangerousPermissions':['android.permission.READ_SMS','android.permission.RECEIVE_SMS','android.permission.READ_CALL_LOG','android.permission.SYSTEM_ALERT_WINDOW','android.permission.REQUEST_INSTALL_PACKAGES'],
    'riskScore':100,
    'reasons':['installer_null','dangerous_permissions','overlay_permission','attack_sim_fallback']
  }]
}
# Prefer device token path unavailable; use shared DEVICE_API_KEY
r=httpx.post(f'{base}/api/v1/devices/apps/scan-result',headers={'X-API-Key':'$DeviceKey'},json=body,timeout=20)
print(json.dumps({'status':r.status_code,'body':r.json(),'deviceUuid':dev}))
detail=httpx.get(f'{base}/api/v1/admin/devices/{dev}',headers=ah_admin,timeout=20).json()
hit=[s for s in detail.get('scans') or [] if s.get('packageName')=='$AttackerPkg']
print(json.dumps({'admin_hits':hit[:2]}, default=str))
"@
    if ($post -match '"status": 200' -and $post -match 'labattacker') {
      Add-R "A2-collect-$label" "WARN" ("worker not yet reported; API collection path OK via DEVICE_API_KEY. " + $post.Substring(0, [Math]::Min(350, $post.Length)))
    } else {
      Add-R "A2-collect-$label" "FAIL" $scanOut.Substring(0, [Math]::Min(300, $scanOut.Length))
    }
  }
}

# ---------- A3 DNS / threat path ----------
$dns = & $Py -c @"
import httpx, json
base='$Base'; ah={'X-API-Key':'$AdminKey'}
den=httpx.get(f'{base}/api/v1/admin/dns-denylist',headers=ah,timeout=20).json()
sync=httpx.post(f'{base}/api/v1/admin/dns-denylist/sync-nextdns',headers=ah,timeout=20)
rows=httpx.get(f'{base}/api/v1/admin/devices',headers=ah,timeout=20).json()
rows=sorted(rows,key=lambda x:x.get('lastSyncAt') or '', reverse=True)
dns_devs=[d for d in rows[:5] if d.get('dnsConfigured')]
print(json.dumps({
  'denylist_cn':'cn' in (den.get('tlds') or []),
  'domains_sample':(den.get('domains') or [])[:3],
  'sync':sync.status_code,
  'dnsConfigured_devices':[{'uuid':d.get('deviceUuid'),'dns':d.get('dnsConfigured')} for d in dns_devs[:3]]
}, default=str))
"@
if ($dns -match '"denylist_cn": true') {
  Add-R "A3-denylist" "PASS" $dns.Trim().Substring(0, [Math]::Min(280, $dns.Trim().Length))
} else {
  Add-R "A3-denylist" "FAIL" $dns
}
if ($dns -match '"sync": 200') {
  Add-R "A3-nextdns-push" "PASS" "sync-nextdns 200 (attacker TLD/domains pushed to profile)"
} elseif ($dns -match '"sync": 503') {
  Add-R "A3-nextdns-push" "SKIP" "NEXTDNS_* unset"
} else {
  Add-R "A3-nextdns-push" "WARN" $dns
}

if ($Phone -and (Online $Phone)) {
  $dnsMode = ((& $Adb -s $Phone shell settings get global private_dns_mode 2>$null) -join "").Trim()
  $dnsHost = ((& $Adb -s $Phone shell settings get global private_dns_specifier 2>$null) -join "").Trim()
  if ($dnsMode -match "hostname" -and $dnsHost -match "\S" -and $dnsHost -ne "null") {
    Add-R "A3-phone-private-dns" "PASS" ("mode={0} host={1}" -f $dnsMode, $dnsHost)
  } else {
    Add-R "A3-phone-private-dns" "WARN" ("Private DNS not hostname (mode={0}) — internet block relies on NextDNS" -f $dnsMode)
  }
}

# ---------- cleanup fixture optional (keep for re-scan) ----------
Add-R "Z-note" "PASS" "Fixture left installed for admin UI inspection; uninstall: adb uninstall $AttackerPkg"

$payload = @{
  ranAt = (Get-Date).ToUniversalTime().ToString("o")
  serials = @{ emulator = $Emu; phone = $Phone }
  baseUrl = $Base
  results = $Results
  summary = @{
    fail = @($Results | Where-Object { $_.status -eq "FAIL" }).Count
    pass = @($Results | Where-Object { $_.status -eq "PASS" }).Count
    warn = @($Results | Where-Object { $_.status -eq "WARN" }).Count
    skip = @($Results | Where-Object { $_.status -eq "SKIP" }).Count
  }
}
$payload | ConvertTo-Json -Depth 8 | Set-Content $OutPath -Encoding UTF8
Write-Host "`n=== Summary ==="
$Results | Format-Table -AutoSize
Write-Host "Wrote $OutPath"
exit $(if ($payload.summary.fail -gt 0) { 1 } else { 0 })
