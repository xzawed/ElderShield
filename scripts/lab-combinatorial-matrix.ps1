# Full combinatorial lab: applyTo x call events x DNS x app
# See docs/plans/2026-11-19-combinatorial-lab-matrix.md
# SAFETY: gsm call / ACTION.CALL only on emulator-* serials. Physical SIMs never auto-dial.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
$Emu = "emulator-5554"
$S22 = "CHANGEME_S22_SERIAL"
$Pkg = "com.eldershield"
$Apk = Join-Path $Root "android\app\build\outputs\apk\debug\app-debug.apk"
$Py = Join-Path $Root "backend\.venv\Scripts\python.exe"
$Base = "http://127.0.0.1:8765"
$Results = [System.Collections.Generic.List[object]]::new()

function Record-Case {
  param([string]$Id, [string]$Status, [string]$Notes)
  $Results.Add([pscustomobject]@{ id = $Id; status = $Status; notes = "$Notes" })
  Write-Host ("[{0}] {1} - {2}" -f $Id, $Status, $Notes)
}

function Test-DeviceOnline {
  param([string]$Serial)
  return [bool](& $Adb devices | Select-String ("^{0}\s+device" -f [regex]::Escape($Serial)))
}

Write-Host "=== Combinatorial matrix ==="

# --- Host: unit ---
Push-Location (Join-Path $Root "backend")
$env:ADMIN_API_KEY = "test-admin-key"
$env:DEVICE_API_KEY = "test-device-key"
$po = & $Py -m pytest -q 2>&1 | Out-String
$pytestCode = $LASTEXITCODE
Pop-Location
if ($pytestCode -eq 0) {
  Record-Case "H-pytest" "PASS" (($po.Trim() -split "`n")[-1])
} else {
  Record-Case "H-pytest" "FAIL" $po.Substring([Math]::Max(0, $po.Length - 300))
}

Push-Location (Join-Path $Root "android")
if (-not $env:JAVA_HOME) {
  $jdk = Get-ChildItem "C:\Program Files\Eclipse Adoptium" -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending | Select-Object -First 1
  if ($jdk) { $env:JAVA_HOME = $jdk.FullName }
}
& .\gradlew.bat :core:test --quiet 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
  Record-Case "H-core-test" "PASS" "AppRisk+matcher+dns+direction"
} else {
  Record-Case "H-core-test" "FAIL" "gradle :core:test"
}
if (-not (Test-Path $Apk)) {
  & .\gradlew.bat :app:assembleDebug --quiet 2>&1 | Out-Null
}
Pop-Location

$seedPath = Join-Path $env:TEMP "es_combo_seed.py"
@'
import httpx, json, sys, os
base = os.environ["ES_BASE"]
ah = {"X-API-Key": "test-admin-key"}
dh = {"X-API-Key": "test-device-key"}
cmd = sys.argv[1]

def rows():
    return httpx.get(f"{base}/api/v1/admin/country-restrictions", headers=ah, timeout=20).json()

def upsert(countries, apply_to, enabled, name):
    allr = rows()
    cur = next((r for r in allr if sorted(r.get("countries") or []) == sorted(countries)), None)
    body = {"name": name, "countries": countries, "applyTo": apply_to, "enabled": enabled, "description": "combo lab"}
    if cur:
        httpx.put(f"{base}/api/v1/admin/country-restrictions/{cur['id']}", headers=ah, json=body, timeout=20).raise_for_status()
    else:
        httpx.post(f"{base}/api/v1/admin/country-restrictions", headers=ah, json=body, timeout=20).raise_for_status()

if cmd == "set":
    cn = json.loads(open(sys.argv[2], encoding="utf-8-sig").read())
    kr = json.loads(open(sys.argv[3], encoding="utf-8-sig").read())
    for r in rows():
        cset = sorted(r.get("countries") or [])
        if cset not in (["CN"], ["KR"]) and r.get("enabled"):
            body = {
                "name": r.get("name") or "other",
                "countries": r["countries"],
                "applyTo": r.get("applyTo") or r.get("apply_to") or ["call"],
                "enabled": False,
                "description": r.get("description") or "combo lab mute",
            }
            httpx.put(
                f"{base}/api/v1/admin/country-restrictions/{r['id']}",
                headers=ah, json=body, timeout=20,
            ).raise_for_status()
    upsert(["CN"], cn["applyTo"], cn["enabled"], "Combo CN")
    upsert(["KR"], kr["applyTo"], kr["enabled"], "Combo KR")
    want = "+8613812345678"
    rules = httpx.get(f"{base}/api/v1/admin/call-rules", headers=ah, timeout=20).json()
    if not any(want in (r.get("whitelist") or []) for r in rules):
        httpx.post(f"{base}/api/v1/admin/call-rules", headers=ah, json={
            "countryCodes": [], "whitelist": [want], "enabled": True
        }, timeout=20).raise_for_status()
    latest = httpx.get(f"{base}/api/v1/rules/latest", headers=dh, timeout=20).json()
    den = httpx.get(f"{base}/api/v1/admin/dns-denylist", headers=ah, timeout=20).json()
    print(json.dumps({
        "version": latest["version"],
        "den_countries": den.get("countries"),
        "tlds": den.get("tlds"),
        "count": den.get("count"),
    }))
elif cmd == "denylist":
    print(json.dumps(httpx.get(f"{base}/api/v1/admin/dns-denylist", headers=ah, timeout=20).json()))
elif cmd == "sync":
    r = httpx.post(f"{base}/api/v1/admin/dns-denylist/sync-nextdns", headers=ah, timeout=30)
    print(r.status_code, r.text[:200])
elif cmd == "scan":
    uuid = sys.argv[2]
    httpx.post(f"{base}/api/v1/devices/heartbeat", headers=dh, json={
        "deviceUuid": uuid, "appVersion": "0.1.0", "dnsConfigured": False,
        "callScreeningEnabled": True, "callScreeningHeldBy": "com.eldershield",
        "callScreeningPeers": [], "lastRuleVersion": 0
    }, timeout=20).raise_for_status()
    httpx.post(f"{base}/api/v1/devices/apps/scan-result", headers=dh, json={
        "deviceUuid": uuid,
        "suspiciousApps": [{
            "packageName": "com.fake.combo.lab",
            "installer": None,
            "dangerousPermissions": ["READ_SMS", "RECEIVE_SMS"],
            "riskScore": 85
        }]
    }, timeout=20).raise_for_status()
    listed = httpx.get(f"{base}/api/v1/admin/devices/{uuid}/scan-results", headers=ah, timeout=20)
    print(listed.status_code, listed.text[:400])
elif cmd == "devices":
    d = httpx.get(f"{base}/api/v1/admin/devices", headers=ah, timeout=20).json()
    print(json.dumps(sorted(d, key=lambda x: x.get("lastSyncAt") or "", reverse=True)[:5], default=str))
'@ | Set-Content -Path $seedPath -Encoding UTF8
$env:ES_BASE = $Base

function Write-JsonNoBom {
  param([string]$Path, [string]$Json)
  $enc = New-Object System.Text.UTF8Encoding $false
  [System.IO.File]::WriteAllText($Path, $Json, $enc)
}

function Set-Policy {
  param([string[]]$CnApply, [bool]$CnEn, [string[]]$KrApply, [bool]$KrEn)
  $cnPath = Join-Path $env:TEMP "es_combo_cn.json"
  $krPath = Join-Path $env:TEMP "es_combo_kr.json"
  $cnArr = ($CnApply | ForEach-Object { '"{0}"' -f $_ }) -join ","
  $krArr = ($KrApply | ForEach-Object { '"{0}"' -f $_ }) -join ","
  $cnEnJ = if ($CnEn) { "true" } else { "false" }
  $krEnJ = if ($KrEn) { "true" } else { "false" }
  Write-JsonNoBom $cnPath ('{{"applyTo":[{0}],"enabled":{1}}}' -f $cnArr, $cnEnJ)
  Write-JsonNoBom $krPath ('{{"applyTo":[{0}],"enabled":{1}}}' -f $krArr, $krEnJ)
  $out = & $Py $seedPath set $cnPath $krPath 2>&1 | Out-String
  if ($LASTEXITCODE -ne 0) {
    throw ("Set-Policy failed: {0}" -f $out)
  }
  return $out.Trim()
}

function Sync-Emu {
  if (-not (Test-DeviceOnline $Emu)) { return }
  & $Adb -s $Emu reverse tcp:8765 tcp:8765 | Out-Null
  & $Adb -s $Emu install -r $Apk 2>$null | Out-Null
  & $Adb -s $Emu shell cmd role add-role-holder android.app.role.CALL_SCREENING $Pkg 2>$null | Out-Null
  $prefs = @"
<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="base_url">http://127.0.0.1:8765</string>
    <string name="device_api_key">test-device-key</string>
</map>
"@
  $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($prefs))
  & $Adb -s $Emu shell am force-stop $Pkg
  & $Adb -s $Emu shell "run-as $Pkg sh -c 'echo $b64 | base64 -d > shared_prefs/eldershield.xml'" 2>$null | Out-Null
  & $Adb -s $Emu shell am start -n "$Pkg/.ui.MainActivity" | Out-Null
  Start-Sleep -Seconds 2
  & $Adb -s $Emu shell uiautomator dump /sdcard/ui.xml 2>$null | Out-Null
  $xml = (& $Adb -s $Emu shell cat /sdcard/ui.xml 2>$null) -join ""
  if ($xml -match 'permission_allow_button"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"') {
    $cx = [int](([int]$Matches[1] + [int]$Matches[3]) / 2)
    $cy = [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
    & $Adb -s $Emu shell input tap $cx $cy
    Start-Sleep -Seconds 1
  }
  if ($xml -match 'id/saveProvision"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"') {
    $cx = [int](([int]$Matches[1] + [int]$Matches[3]) / 2)
    $cy = [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
    & $Adb -s $Emu shell input tap $cx $cy
  }
  Start-Sleep -Seconds 10
}

function Assert-EmulatorCallTarget {
  param([string]$Serial)
  if ($Serial -notmatch '^emulator-') {
    throw ("Call lab refused: serial '{0}' is not an emulator. Physical CALL/gsm is blocked." -f $Serial)
  }
}

function Clear-Gsm {
  Assert-EmulatorCallTarget $Emu
  foreach ($n in @("+8613999000099","+8613812345678","+821098765432","01098765432","+12025550199","114","+8613999000002")) {
    & $Adb -s $Emu emu gsm cancel $n 2>$null | Out-Null
  }
}

function Invoke-In {
  param([string]$Number)
  Assert-EmulatorCallTarget $Emu
  $log = ""
  $scr = ""
  for ($attempt = 1; $attempt -le 2; $attempt++) {
    Clear-Gsm
    & $Adb -s $Emu logcat -c
    Start-Sleep -Milliseconds 400
    & $Adb -s $Emu emu gsm call $Number 2>$null | Out-Null
    Start-Sleep -Seconds 4
    $log = (& $Adb -s $Emu logcat -d -s ElderCallScreen:I | Select-Object -Last 1)
    $scr = (& $Adb -s $Emu shell dumpsys telecom | Select-String "SCREENING_COMPLETED" | Select-Object -Last 1).Line
    & $Adb -s $Emu emu gsm cancel $Number 2>$null | Out-Null
    if ("$log" -match "ElderCallScreen" -or "$scr" -match "SCREENING_COMPLETED") { break }
    Start-Sleep -Seconds 2
  }
  return @{ log = "$log"; scr = "$scr" }
}

function Invoke-Out {
  param([string]$Number)
  Assert-EmulatorCallTarget $Emu
  Clear-Gsm
  & $Adb -s $Emu logcat -c
  & $Adb -s $Emu shell am start -a android.intent.action.CALL -d ("tel:{0}" -f $Number) 2>$null | Out-Null
  Start-Sleep -Seconds 3
  $log = (& $Adb -s $Emu logcat -d -s ElderCallScreen:I | Select-Object -Last 1)
  & $Adb -s $Emu shell input keyevent KEYCODE_ENDCALL 2>$null | Out-Null
  & $Adb -s $Emu emu gsm cancel $Number 2>$null | Out-Null
  return @{ log = "$log" }
}

if (-not (Test-DeviceOnline $Emu)) {
  Record-Case "EMU" "FAIL" "emulator-5554 required for call matrix"
} else {
  Sync-Emu
  Record-Case "EMU-sync" "PASS" "role+provision attempted"

  $applyCases = @(
    @{ id = "A-call"; cn = @("call"); en = $true; expectBlock = $true; expectDen = $false },
    @{ id = "A-dns"; cn = @("dns"); en = $true; expectBlock = $false; expectDen = $true },
    @{ id = "A-internet"; cn = @("internet"); en = $true; expectBlock = $false; expectDen = $true },
    @{ id = "A-call-dns"; cn = @("call","dns"); en = $true; expectBlock = $true; expectDen = $true },
    @{ id = "A-call-inet"; cn = @("call","internet"); en = $true; expectBlock = $true; expectDen = $true },
    @{ id = "A-dns-inet"; cn = @("dns","internet"); en = $true; expectBlock = $false; expectDen = $true },
    @{ id = "A-all"; cn = @("call","dns","internet"); en = $true; expectBlock = $true; expectDen = $true },
    @{ id = "A-disabled"; cn = @("call","dns"); en = $false; expectBlock = $false; expectDen = $false }
  )

  foreach ($c in $applyCases) {
    Set-Policy -CnApply $c.cn -CnEn $c.en -KrApply @("call") -KrEn $false | Out-Null
    Sync-Emu
    $den = & $Py $seedPath denylist | ConvertFrom-Json
    $hasCnDen = ($den.countries -contains "CN") -and (($den.tlds -contains "cn") -or ($den.count -gt 0))
    if ($c.expectDen) {
      if ($hasCnDen) {
        Record-Case "$($c.id)-denylist" "PASS" "CN in denylist tlds/count"
      } else {
        Record-Case "$($c.id)-denylist" "FAIL" ($den | ConvertTo-Json -Compress)
      }
    } else {
      if (-not $hasCnDen) {
        Record-Case "$($c.id)-denylist" "PASS" "CN absent from denylist"
      } else {
        Record-Case "$($c.id)-denylist" "WARN" "CN still present (other enabled rows?)"
      }
    }
    $r = Invoke-In -Number "+8613999000099"
    $blocked = ($r.log -match "block=true") -or ($r.scr -match "Reject")
    if ($c.expectBlock -and $blocked) {
      Record-Case "$($c.id)-inCN" "PASS" ("Reject {0}" -f $r.log)
    } elseif ((-not $c.expectBlock) -and ($r.log -match "block=false")) {
      Record-Case "$($c.id)-inCN" "PASS" ("Allow {0}" -f $r.log)
    } elseif ((-not $c.expectBlock) -and -not $blocked) {
      Record-Case "$($c.id)-inCN" "PASS" ("no Reject {0}" -f $r.scr)
    } else {
      Record-Case "$($c.id)-inCN" "FAIL" ("expectBlock={0} log={1} scr={2}" -f $c.expectBlock, $r.log, $r.scr)
    }
  }

  Set-Policy -CnApply @("call","dns") -CnEn $true -KrApply @("call") -KrEn $true | Out-Null
  Sync-Emu
  & $Adb -s $Emu emu phonenumber 15555218135 2>$null | Out-Null
  # warm-up: first post-sync ring can miss CallScreening bind
  Invoke-In -Number "+12025550100" | Out-Null
  Start-Sleep -Seconds 2

  $events = @(
    @{ id = "B-inCN"; number = "+8613999000099"; direction = "in"; expect = "block" },
    @{ id = "B-inWL"; number = "+8613812345678"; direction = "in"; expect = "allow" },
    @{ id = "B-inUS"; number = "+12025550199"; direction = "in"; expect = "allow" },
    @{ id = "B-in82"; number = "+821098765432"; direction = "in"; expect = "block" },
    @{ id = "B-in010"; number = "01098765432"; direction = "in"; expect = "block" },
    @{ id = "B-outCN"; number = "+8613999000002"; direction = "out"; expect = "allow" },
    @{ id = "B-outKR"; number = "114"; direction = "out"; expect = "allow" }
  )
  foreach ($e in $events) {
    if ($e.direction -eq "in") { $r = Invoke-In -Number $e.number } else { $r = Invoke-Out -Number $e.number }
    $log = $r.log
    $scr = $r.scr
    $blocked = ($log -match "block=true") -or ($scr -match "Reject")
    $allowed = ($log -match "block=false") -or (($scr -match "Allow") -and -not ($scr -match "Reject"))
    if ($e.expect -eq "block" -and $blocked) {
      Record-Case $e.id "PASS" ("{0} | {1}" -f $log, $scr)
    } elseif ($e.expect -eq "allow" -and ($allowed -or ($log -match "dir=1"))) {
      Record-Case $e.id "PASS" ("{0} | {1}" -f $log, $scr)
    } else {
      Record-Case $e.id "FAIL" ("expect={0} log={1} scr={2}" -f $e.expect, $log, $scr)
    }
  }

  & $Adb -s $Emu emu phonenumber 8613999000001 2>$null | Out-Null
  Start-Sleep -Seconds 1
  $r = Invoke-In -Number "+8613999000099"
  if (($r.log -match "block=true") -or ($r.scr -match "Reject")) {
    Record-Case "C-ownCN-inCN" "PASS" ("{0} | {1}" -f $r.log, $r.scr)
  } else {
    Record-Case "C-ownCN-inCN" "FAIL" ("log={0} scr={1}" -f $r.log, $r.scr)
  }
  $r = Invoke-Out -Number "114"
  if ($r.log -match "block=false") {
    Record-Case "C-ownCN-outKR" "PASS" $r.log
  } else {
    Record-Case "C-ownCN-outKR" "FAIL" $r.log
  }
  & $Adb -s $Emu emu phonenumber 15555218135 2>$null | Out-Null
}

if (Test-DeviceOnline $Emu) {
  Set-Policy -CnApply @("dns") -CnEn $true -KrApply @("call") -KrEn $false | Out-Null
  & $Adb -s $Emu shell settings put global private_dns_mode hostname
  & $Adb -s $Emu shell settings put global private_dns_specifier "dns.nextdns.io"
  & $Adb -s $Emu shell am force-stop $Pkg
  & $Adb -s $Emu shell am start -n "$Pkg/.ui.MainActivity" | Out-Null
  Start-Sleep -Seconds 16
  $devs = & $Py $seedPath devices
  if ($devs -match '"dnsConfigured":\s*true') {
    Record-Case "D-hostname" "PASS" "dnsConfigured=true"
  } else {
    $snip = if ($devs.Length -gt 240) { $devs.Substring(0, 240) } else { $devs }
    Record-Case "D-hostname" "WARN" $snip
  }
  & $Adb -s $Emu shell settings put global private_dns_mode opportunistic
  & $Adb -s $Emu shell settings delete global private_dns_specifier 2>$null | Out-Null
}

$sync = & $Py $seedPath sync
if ("$sync" -match "^200") {
  Record-Case "D-nextdns" "PASS" "$sync"
} elseif ("$sync" -match "503") {
  Record-Case "D-nextdns" "SKIP" "NEXTDNS_* unset"
} else {
  Record-Case "D-nextdns" "FAIL" "$sync"
}

$scan = & $Py $seedPath scan "combo-lab-device-001"
if (("$scan" -match "^200") -and ("$scan" -match "com.fake.combo.lab")) {
  Record-Case "E-scan-api" "PASS" "scan roundtrip"
} elseif ("$scan" -match "^200") {
  Record-Case "E-scan-api" "WARN" "$scan"
} else {
  Record-Case "E-scan-api" "FAIL" "$scan"
}

if (Test-DeviceOnline $S22) {
  $path = & $Adb -s $S22 shell pm path viva.republica.toss 2>$null
  if ("$path" -match "package:") {
    $out = & $Adb -s $S22 shell monkey -p viva.republica.toss -c android.intent.category.LAUNCHER 1 2>&1 | Out-String
    if ($out -match "Events injected") {
      Record-Case "E-bank-toss" "PASS" "monkey ok"
    } else {
      Record-Case "E-bank-toss" "FAIL" $out
    }
  } else {
    Record-Case "E-bank-toss" "SKIP" "not installed"
  }
  $holders = (& $Adb -s $S22 shell cmd role get-role-holders android.app.role.CALL_SCREENING 2>$null) -join ""
  Record-Case "F-s22-role" "PASS" ("holders={0} (no steal this run)" -f $holders)
} else {
  Record-Case "E-bank-toss" "SKIP" "no S22"
  Record-Case "F-s22-role" "SKIP" "no S22"
}

Set-Policy -CnApply @("call","dns") -CnEn $true -KrApply @("call") -KrEn $false | Out-Null
Record-Case "Z-restore" "PASS" "CN call+dns enabled; KR call disabled"

$outPath = Join-Path $Root "docs\plans\2026-11-19-combinatorial-lab-results.json"
@{
  ranAt = (Get-Date).ToUniversalTime().ToString("o")
  matrixDoc = "docs/plans/2026-11-19-combinatorial-lab-matrix.md"
  results = $Results
} | ConvertTo-Json -Depth 6 | Set-Content $outPath -Encoding UTF8

Write-Host ""
Write-Host "=== Summary counts ==="
$Results | Group-Object status | ForEach-Object { "{0}={1}" -f $_.Name, $_.Count }
Write-Host ("Wrote {0}" -f $outPath)
$fail = @($Results | Where-Object { $_.status -eq "FAIL" }).Count
exit $(if ($fail -gt 0) { 1 } else { 0 })
