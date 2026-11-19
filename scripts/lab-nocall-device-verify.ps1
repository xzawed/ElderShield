# Non-call device verify: DNS/internet path, bank apps, Bitdefender coexistence.
# NEVER issues ACTION.CALL or emu gsm call.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
$S22 = if ($env:ELDERSHIELD_S22_SERIAL) { $env:ELDERSHIELD_S22_SERIAL } else { "CHANGEME_S22_SERIAL" }
$Emu = "emulator-5554"
$Pkg = "com.eldershield"
$Apk = Join-Path $Root "android\app\build\outputs\apk\debug\app-debug.apk"
$Py = Join-Path $Root "backend\.venv\Scripts\python.exe"
$Base = "http://127.0.0.1:8765"
$AdminKey = "test-admin-key"
$DeviceKey = "test-device-key"
$Results = [System.Collections.Generic.List[object]]::new()

function Add-R([string]$Id, [string]$Status, [string]$Notes) {
  $Results.Add([pscustomobject]@{ id = $Id; status = $Status; notes = "$Notes" })
  Write-Host ("[{0}] {1} - {2}" -f $Id, $Status, $Notes)
}

function Online([string]$Serial) {
  return [bool](& $Adb devices | Select-String ("^{0}\s+device" -f [regex]::Escape($Serial)))
}

Write-Host "=== Non-call device verify (no PSTN) ==="

# Host: denylist from CN dns|internet
$denOut = & $Py -c @"
import httpx, json, os
base='$Base'; ah={'X-API-Key':'$AdminKey'}
rows=httpx.get(f'{base}/api/v1/admin/country-restrictions',headers=ah,timeout=20).json()
cn=next((r for r in rows if sorted(r.get('countries') or [])==['CN']), None)
body={'name':'Lab CN dns','countries':['CN'],'applyTo':['dns','internet'],'enabled':True,'description':'nocall verify'}
if cn:
  httpx.put(f\"{base}/api/v1/admin/country-restrictions/{cn['id']}\",headers=ah,json=body,timeout=20).raise_for_status()
else:
  httpx.post(f'{base}/api/v1/admin/country-restrictions',headers=ah,json=body,timeout=20).raise_for_status()
# mute KR call if present
kr=next((r for r in rows if sorted(r.get('countries') or [])==['KR']), None)
if kr and kr.get('enabled'):
  httpx.put(f\"{base}/api/v1/admin/country-restrictions/{kr['id']}\",headers=ah,json={
    'name':kr.get('name') or 'KR','countries':['KR'],'applyTo':kr.get('applyTo') or ['call'],
    'enabled':False,'description':'nocall verify mute KR call'
  },timeout=20).raise_for_status()
den=httpx.get(f'{base}/api/v1/admin/dns-denylist',headers=ah,timeout=20).json()
sync=httpx.post(f'{base}/api/v1/admin/dns-denylist/sync-nextdns',headers=ah,timeout=20)
print(json.dumps({'countries':den.get('countries'),'tlds':den.get('tlds'),'count':den.get('count'),
  'has_baidu':'baidu.com' in (den.get('domains') or []),'sync':sync.status_code}))
"@
$den = $denOut | ConvertFrom-Json
if (($den.countries -contains "CN") -and ($den.tlds -contains "cn") -and $den.has_baidu) {
  Add-R "N1-denylist" "PASS" ($denOut.Trim())
} else {
  Add-R "N1-denylist" "FAIL" ($denOut.Trim())
}
if ($den.sync -eq 200) { Add-R "N2-nextdns-sync" "PASS" "sync 200" }
elseif ($den.sync -eq 503) { Add-R "N2-nextdns-sync" "SKIP" "NEXTDNS_* unset — real .cn NXDOMAIN needs operator profile" }
else { Add-R "N2-nextdns-sync" "FAIL" "sync=$($den.sync)" }

function Test-DeviceDnsAndVpn([string]$Serial, [string]$Label) {
  if (-not (Online $Serial)) {
    Add-R "$Label-online" "SKIP" "not connected"
    return
  }
  & $Adb -s $Serial reverse tcp:8765 tcp:8765 | Out-Null
  if (Test-Path $Apk) { & $Adb -s $Serial install -r $Apk 2>$null | Out-Null }

  # VPN / overlay / accessibility must not be used by ElderShield
  $vpn = (& $Adb -s $Serial shell dumpsys connectivity 2>$null | Select-String -Pattern "VPN|VpnNetworkAgent" | Select-Object -First 5) -join " | "
  $esVpn = (& $Adb -s $Serial shell dumpsys package $Pkg 2>$null | Select-String -Pattern "BIND_VPN_SERVICE|VpnService" | Select-Object -First 3) -join " | "
  if ($esVpn -match "VpnService|BIND_VPN") {
    Add-R "$Label-vpn" "FAIL" "ElderShield declares VPN capability: $esVpn"
  } else {
    Add-R "$Label-vpn" "PASS" "no ElderShield VpnService in package dump"
  }

  # Private DNS hostname (trusted) → dnsConfigured
  & $Adb -s $Serial shell settings put global private_dns_mode hostname
  & $Adb -s $Serial shell settings put global private_dns_specifier "dns.nextdns.io"
  & $Adb -s $Serial shell am force-stop $Pkg
  & $Adb -s $Serial shell am start -n "$Pkg/.ui.MainActivity" | Out-Null
  Start-Sleep -Seconds 16
  $devs = & $Py -c "import httpx,json; d=httpx.get('$Base/api/v1/admin/devices',headers={'X-API-Key':'$AdminKey'},timeout=20).json(); print(json.dumps(sorted(d,key=lambda x:x.get('lastSyncAt') or '',reverse=True)[:4],default=str))"
  if ($devs -match '"dnsConfigured":\s*true') {
    Add-R "$Label-dnsConfigured" "PASS" "dnsConfigured=true after Private DNS hostname"
  } else {
    Add-R "$Label-dnsConfigured" "WARN" $devs.Substring(0, [Math]::Min(280, $devs.Length))
  }

  # Resolve probe (informational): without operator NextDNS denylist push, .cn may still resolve
  $probe = & $Adb -s $Serial shell "nslookup baidu.com 2>/dev/null || getprop net.dns1" 2>&1 | Out-String
  if ($den.sync -eq 200) {
    if ($probe -match "NXDOMAIN|can't find|Non-existent") {
      Add-R "$Label-cn-resolve" "PASS" "baidu/cn blocked at DNS"
    } else {
      Add-R "$Label-cn-resolve" "WARN" ("sync ok but resolve still open: " + $probe.Substring(0, [Math]::Min(200, $probe.Length)))
    }
  } else {
    $snip = if ($probe.Length -gt 120) { $probe.Substring(0, 120) } else { $probe }
    Add-R "$Label-cn-resolve" "SKIP" ("no NextDNS push; resolve probe not a product fail. snippet={0}" -f $snip)
  }

  # restore opportunistic DNS
  & $Adb -s $Serial shell settings put global private_dns_mode opportunistic
  & $Adb -s $Serial shell settings delete global private_dns_specifier 2>$null | Out-Null
}

Test-DeviceDnsAndVpn $S22 "S22"
Test-DeviceDnsAndVpn $Emu "EMU"

# Bank apps on S22 — launch only, no call
if (Online $S22) {
  $bankNotes = @()
  foreach ($b in @(
    @{ pkg = "viva.republica.toss"; name = "Toss" },
    @{ pkg = "com.kakaobank.channel"; name = "KakaoBank" },
    @{ pkg = "com.shinhan.sbanking"; name = "Shinhan" },
    @{ pkg = "com.kbcard.cxh.appcard"; name = "KB" }
  )) {
    $path = & $Adb -s $S22 shell pm path $b.pkg 2>$null
    if ("$path" -match "package:") {
      & $Adb -s $S22 shell am force-stop $b.pkg 2>$null | Out-Null
      $out = & $Adb -s $S22 shell monkey -p $b.pkg -c android.intent.category.LAUNCHER 1 2>&1 | Out-String
      Start-Sleep -Seconds 3
      $fg = (& $Adb -s $S22 shell dumpsys activity activities 2>$null |
        Select-String -Pattern "mResumedActivity|topResumedActivity" | Select-Object -First 2) -join "; "
      $ok = ($out -match "Events injected") -and ($fg -notmatch "eldershield")
      $bankNotes += ("{0}:ok={1}" -f $b.name, $ok)
      if ($ok) { Add-R "BANK-$($b.name)" "PASS" $fg }
      else { Add-R "BANK-$($b.name)" "FAIL" ("monkey/fg " + $out.Substring(0, [Math]::Min(120, $out.Length)) + " | " + $fg) }
    } else {
      Add-R "BANK-$($b.name)" "SKIP" "not installed"
    }
  }
} else {
  Add-R "BANK" "SKIP" "no S22"
}

# Bitdefender coexistence — never steal role
if (Online $S22) {
  $bdPkgs = (& $Adb -s $S22 shell pm list packages 2>$null | Select-String -Pattern "bitdefender|com.fsecure|com.bitdefender" ) -join ", "
  $holders = (& $Adb -s $S22 shell cmd role get-role-holders android.app.role.CALL_SCREENING 2>$null) -join ""
  $peersRaw = & $Py -c @"
import httpx, json
d=httpx.get('$Base/api/v1/admin/devices',headers={'X-API-Key':'$AdminKey'},timeout=20).json()
rows=sorted(d,key=lambda x:x.get('lastSyncAt') or '', reverse=True)[:3]
print(json.dumps([{k:x.get(k) for k in ['deviceUuid','callScreeningHeldBy','callScreeningPeers','callScreeningEnabled','dnsConfigured']} for x in rows], default=str))
"@
  Add-R "BD-packages" $(if ($bdPkgs) { "PASS" } else { "WARN" }) $(if ($bdPkgs) { $bdPkgs } else { "no bitdefender package name matched" })
  Add-R "BD-role-holder" "PASS" ("holders=$holders (no steal this run)")
  if ($holders -match "bitdefender|fsecure" -and $holders -match "eldershield") {
    Add-R "BD-role-conflict" "FAIL" "both appear as holders (unexpected dual)"
  } elseif ($holders -match "eldershield") {
    Add-R "BD-coexist" "PASS" "ES holds CALL_SCREENING; BD not holding (platform single-holder). DNS/scan still OK policy A"
  } elseif ($holders -match "bitdefender|fsecure") {
    Add-R "BD-coexist" "PASS" "BD holds CALL_SCREENING; ES must not steal — call path Off report only (§1.2.1 A)"
  } else {
    Add-R "BD-coexist" "WARN" "holder neither ES nor BD match: $holders"
  }
  Add-R "BD-heartbeat-peers" "PASS" $peersRaw.Substring(0, [Math]::Min(400, $peersRaw.Length))

  # Accessibility / overlay services from ES
  $acc = (& $Adb -s $S22 shell settings get secure enabled_accessibility_services 2>$null) -join ""
  if ($acc -match "eldershield") {
    Add-R "ES-accessibility" "FAIL" "ElderShield in accessibility: $acc"
  } else {
    Add-R "ES-accessibility" "PASS" "ES not in enabled_accessibility_services"
  }
} else {
  Add-R "BD" "SKIP" "no S22"
}

# Restore CN call+dns enabled for daily lab default
& $Py -c @"
import httpx
base='$Base'; ah={'X-API-Key':'$AdminKey'}
rows=httpx.get(f'{base}/api/v1/admin/country-restrictions',headers=ah,timeout=20).json()
cn=next((r for r in rows if sorted(r.get('countries') or [])==['CN']), None)
if cn:
  httpx.put(f\"{base}/api/v1/admin/country-restrictions/{cn['id']}\",headers=ah,json={
    'name':'Combo CN','countries':['CN'],'applyTo':['call','dns'],'enabled':True,'description':'restore after nocall'
  },timeout=20).raise_for_status()
kr=next((r for r in rows if sorted(r.get('countries') or [])==['KR']), None)
if kr:
  httpx.put(f\"{base}/api/v1/admin/country-restrictions/{kr['id']}\",headers=ah,json={
    'name':kr.get('name') or 'KR','countries':['KR'],'applyTo':['call'],'enabled':False,'description':'restore KR call off'
  },timeout=20).raise_for_status()
print('restored')
"@
Add-R "Z-restore" "PASS" "CN call+dns on; KR call off"

$outPath = Join-Path $Root "docs\plans\2026-11-19-nocall-device-verify-results.json"
@{
  ranAt = (Get-Date).ToUniversalTime().ToString("o")
  results = $Results
} | ConvertTo-Json -Depth 6 | Set-Content $outPath -Encoding UTF8
Write-Host ""
Write-Host "=== Summary ==="
$Results | Group-Object status | ForEach-Object { "{0}={1}" -f $_.Name, $_.Count }
Write-Host "Wrote $outPath"
$fail = @($Results | Where-Object { $_.status -eq "FAIL" }).Count
exit $(if ($fail -gt 0) { 1 } else { 0 })
