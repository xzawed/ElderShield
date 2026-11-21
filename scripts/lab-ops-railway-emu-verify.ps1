# Precise ops verification: emulator against Railway production rules.
# SAFETY: gsm inject only on emulator-*.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
$Emu = "emulator-5554"
$Pkg = "com.eldershield"
$AttackerPkg = "com.eldershield.labattacker"
$Apk = Join-Path $Root "android\app\build\outputs\apk\debug\app-debug.apk"
$AttackerApk = Join-Path $Root "android\lab-attacker-fixture\build\outputs\apk\debug\lab-attacker-fixture-debug.apk"
$Py = Join-Path $Root "backend\.venv\Scripts\python.exe"
$Base = if ($env:ELDERSHIELD_LAB_URL) { $env:ELDERSHIELD_LAB_URL } else { "https://eldershield.up.railway.app" }
$KeysPath = if ($env:ELDERSHIELD_KEYS_JSON) { $env:ELDERSHIELD_KEYS_JSON } else { Join-Path $env:TEMP "es-keys.json" }
$Date = Get-Date -Format "yyyy-MM-dd"
$OutPath = Join-Path $Root "docs\plans\$Date-ops-railway-emu-verify-results.json"
$Results = [System.Collections.Generic.List[object]]::new()

function Add-R([string]$Id, [string]$Status, [string]$Notes) {
  $Results.Add([pscustomobject]@{ id = $Id; status = $Status; notes = "$Notes"; at = (Get-Date).ToString("o") })
  Write-Host ("[{0}] {1} — {2}" -f $Id, $Status, $Notes)
}

function Online([string]$Serial) {
  return [bool](& $Adb devices | Select-String ("^{0}\s+device" -f [regex]::Escape($Serial)))
}

if (-not (Test-Path $KeysPath)) { throw "Missing keys JSON: $KeysPath" }
$keys = Get-Content $KeysPath -Raw | ConvertFrom-Json
$AdminKey = $keys.ADMIN_API_KEY
$DeviceKey = $keys.DEVICE_API_KEY
$ah = @{ "X-API-Key" = $AdminKey }
$dh = @{ "X-API-Key" = $DeviceKey }

Write-Host "=== Ops Railway emu verify ==="
Write-Host "Base=$Base emu=$(Online $Emu)"

# O0 health + snapshot
try {
  $health = Invoke-RestMethod -Uri "$Base/health" -TimeoutSec 20
  Add-R "O0-health" "PASS" ("bundleVersion={0} devices={1}" -f $health.bundleVersion, $health.devices)
} catch {
  Add-R "O0-health" "FAIL" $_.Exception.Message
  $Results | ConvertTo-Json -Depth 6 | Set-Content $OutPath -Encoding UTF8
  exit 1
}

$restr = Invoke-RestMethod -Uri "$Base/api/v1/admin/country-restrictions" -Headers $ah
$den = Invoke-RestMethod -Uri "$Base/api/v1/admin/dns-denylist" -Headers $ah
$latest = Invoke-RestMethod -Uri "$Base/api/v1/rules/latest" -Headers $dh
$active = @($restr | Where-Object { $_.enabled })
$allCountries = @()
foreach ($r in $active) { $allCountries += @($r.countries) }
$allCountries = $allCountries | ForEach-Object { "$_".ToUpper() } | Select-Object -Unique
$apply = @($active | ForEach-Object { @($_.applyTo) }) | Select-Object -Unique
Add-R "O0-snapshot" "PASS" ("restrictions={0} countries={1} apply=[{2}] denylistTlds={3} rulesVer={4}" -f $active.Count, $allCountries.Count, ($apply -join ','), @($den.tlds).Count, $latest.version)

# Known Android matcher coverage (product code DEFAULT_CALLING_CODES)
$AndroidCodes = @("CN","RU","KP","IR","KR","US","JP")
$covered = @($allCountries | Where-Object { $AndroidCodes -contains $_ })
$uncovered = @($allCountries | Where-Object { $AndroidCodes -notcontains $_ })
Add-R "O0-matcher-coverage" "INFO" ("restricted={0} androidCallingCodeMapHit={1} miss={2} (miss samples: {3})" -f $allCountries.Count, $covered.Count, $uncovered.Count, (($uncovered | Select-Object -First 12) -join ','))

if (-not (Online $Emu)) {
  Add-R "O1-emu" "FAIL" "emulator-5554 not connected"
  $Results | ConvertTo-Json -Depth 6 | Set-Content $OutPath -Encoding UTF8
  exit 1
}
if ($Emu -notmatch '^emulator-') { throw "refused non-emulator" }

# Build APKs if needed
Push-Location (Join-Path $Root "android")
& .\gradlew.bat :app:assembleDebug :lab-attacker-fixture:assembleDebug --no-daemon 2>&1 | Out-Null
Pop-Location
if (-not (Test-Path $Apk)) { Add-R "O1-apk" "FAIL" "debug apk missing" } else { Add-R "O1-apk" "PASS" "assembleDebug" }

& $Adb -s $Emu shell pm clear $Pkg 2>&1 | Out-Null
& $Adb -s $Emu install -r $Apk 2>&1 | Out-Null
# Provision via legacy prefs workers read
$prefs = @"
<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="base_url">$Base</string>
    <string name="device_api_key">$DeviceKey</string>
</map>
"@
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($prefs))
& $Adb -s $Emu shell "run-as $Pkg mkdir -p shared_prefs" | Out-Null
& $Adb -s $Emu shell "run-as $Pkg sh -c 'echo $b64 | base64 -d > shared_prefs/eldershield.xml'" | Out-Null
& $Adb -s $Emu shell am force-stop $Pkg
& $Adb -s $Emu shell am start -n "$Pkg/.ui.MainActivity" | Out-Null
Start-Sleep -Seconds 2
& $Adb -s $Emu shell uiautomator dump /sdcard/ui.xml 2>$null | Out-Null
$xml = (& $Adb -s $Emu shell cat /sdcard/ui.xml 2>$null) -join ""
if ($xml -match 'resource-id="com.eldershield:id/saveProvision"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"') {
  $cx = [int](([int]$Matches[1] + [int]$Matches[3]) / 2)
  $cy = [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
  & $Adb -s $Emu shell input tap $cx $cy
} elseif ($xml -match 'text="Save[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"') {
  $cx = [int](([int]$Matches[1] + [int]$Matches[3]) / 2)
  $cy = [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
  & $Adb -s $Emu shell input tap $cx $cy
}
Start-Sleep -Seconds 18

$devs = Invoke-RestMethod -Uri "$Base/api/v1/admin/devices" -Headers $ah
$recent = @($devs | Sort-Object { $_.lastSyncAt } -Descending | Select-Object -First 5)
$synced = $recent | Where-Object { # Precise ops verification: emulator against Railway production rules.
# SAFETY: gsm inject only on emulator-*.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
$Emu = "emulator-5554"
$Pkg = "com.eldershield"
$AttackerPkg = "com.eldershield.labattacker"
$Apk = Join-Path $Root "android\app\build\outputs\apk\debug\app-debug.apk"
$AttackerApk = Join-Path $Root "android\lab-attacker-fixture\build\outputs\apk\debug\lab-attacker-fixture-debug.apk"
$Py = Join-Path $Root "backend\.venv\Scripts\python.exe"
$Base = if ($env:ELDERSHIELD_LAB_URL) { $env:ELDERSHIELD_LAB_URL } else { "https://eldershield.up.railway.app" }
$KeysPath = if ($env:ELDERSHIELD_KEYS_JSON) { $env:ELDERSHIELD_KEYS_JSON } else { Join-Path $env:TEMP "es-keys.json" }
$Date = Get-Date -Format "yyyy-MM-dd"
$OutPath = Join-Path $Root "docs\plans\$Date-ops-railway-emu-verify-results.json"
$Results = [System.Collections.Generic.List[object]]::new()

function Add-R([string]$Id, [string]$Status, [string]$Notes) {
  $Results.Add([pscustomobject]@{ id = $Id; status = $Status; notes = "$Notes"; at = (Get-Date).ToString("o") })
  Write-Host ("[{0}] {1} — {2}" -f $Id, $Status, $Notes)
}

function Online([string]$Serial) {
  return [bool](& $Adb devices | Select-String ("^{0}\s+device" -f [regex]::Escape($Serial)))
}

if (-not (Test-Path $KeysPath)) { throw "Missing keys JSON: $KeysPath" }
$keys = Get-Content $KeysPath -Raw | ConvertFrom-Json
$AdminKey = $keys.ADMIN_API_KEY
$DeviceKey = $keys.DEVICE_API_KEY
$ah = @{ "X-API-Key" = $AdminKey }
$dh = @{ "X-API-Key" = $DeviceKey }

Write-Host "=== Ops Railway emu verify ==="
Write-Host "Base=$Base emu=$(Online $Emu)"

# O0 health + snapshot
try {
  $health = Invoke-RestMethod -Uri "$Base/health" -TimeoutSec 20
  Add-R "O0-health" "PASS" ("bundleVersion={0} devices={1}" -f $health.bundleVersion, $health.devices)
} catch {
  Add-R "O0-health" "FAIL" $_.Exception.Message
  $Results | ConvertTo-Json -Depth 6 | Set-Content $OutPath -Encoding UTF8
  exit 1
}

$restr = Invoke-RestMethod -Uri "$Base/api/v1/admin/country-restrictions" -Headers $ah
$den = Invoke-RestMethod -Uri "$Base/api/v1/admin/dns-denylist" -Headers $ah
$latest = Invoke-RestMethod -Uri "$Base/api/v1/rules/latest" -Headers $dh
$active = @($restr | Where-Object { $_.enabled })
$allCountries = @()
foreach ($r in $active) { $allCountries += @($r.countries) }
$allCountries = $allCountries | ForEach-Object { "$_".ToUpper() } | Select-Object -Unique
$apply = @($active | ForEach-Object { @($_.applyTo) }) | Select-Object -Unique
Add-R "O0-snapshot" "PASS" ("restrictions={0} countries={1} apply=[{2}] denylistTlds={3} rulesVer={4}" -f $active.Count, $allCountries.Count, ($apply -join ','), @($den.tlds).Count, $latest.version)

# Known Android matcher coverage (product code DEFAULT_CALLING_CODES)
$AndroidCodes = @("CN","RU","KP","IR","KR","US","JP")
$covered = @($allCountries | Where-Object { $AndroidCodes -contains $_ })
$uncovered = @($allCountries | Where-Object { $AndroidCodes -notcontains $_ })
Add-R "O0-matcher-coverage" "INFO" ("restricted={0} androidCallingCodeMapHit={1} miss={2} (miss samples: {3})" -f $allCountries.Count, $covered.Count, $uncovered.Count, (($uncovered | Select-Object -First 12) -join ','))

if (-not (Online $Emu)) {
  Add-R "O1-emu" "FAIL" "emulator-5554 not connected"
  $Results | ConvertTo-Json -Depth 6 | Set-Content $OutPath -Encoding UTF8
  exit 1
}
if ($Emu -notmatch '^emulator-') { throw "refused non-emulator" }

# Build APKs if needed
Push-Location (Join-Path $Root "android")
& .\gradlew.bat :app:assembleDebug :lab-attacker-fixture:assembleDebug --no-daemon 2>&1 | Out-Null
Pop-Location
if (-not (Test-Path $Apk)) { Add-R "O1-apk" "FAIL" "debug apk missing" } else { Add-R "O1-apk" "PASS" "assembleDebug" }

& $Adb -s $Emu shell pm clear $Pkg 2>&1 | Out-Null
& $Adb -s $Emu install -r $Apk 2>&1 | Out-Null
# Provision via legacy prefs workers read
$prefs = @"
<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="base_url">$Base</string>
    <string name="device_api_key">$DeviceKey</string>
</map>
"@
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($prefs))
& $Adb -s $Emu shell "run-as $Pkg mkdir -p shared_prefs" | Out-Null
& $Adb -s $Emu shell "run-as $Pkg sh -c 'echo $b64 | base64 -d > shared_prefs/eldershield.xml'" | Out-Null
& $Adb -s $Emu shell am force-stop $Pkg
& $Adb -s $Emu shell am start -n "$Pkg/.ui.MainActivity" | Out-Null
Start-Sleep -Seconds 2
& $Adb -s $Emu shell uiautomator dump /sdcard/ui.xml 2>$null | Out-Null
$xml = (& $Adb -s $Emu shell cat /sdcard/ui.xml 2>$null) -join ""
if ($xml -match 'resource-id="com.eldershield:id/saveProvision"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"') {
  $cx = [int](([int]$Matches[1] + [int]$Matches[3]) / 2)
  $cy = [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
  & $Adb -s $Emu shell input tap $cx $cy
} elseif ($xml -match 'text="Save[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"') {
  $cx = [int](([int]$Matches[1] + [int]$Matches[3]) / 2)
  $cy = [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
  & $Adb -s $Emu shell input tap $cx $cy
}
Start-Sleep -Seconds 18

$devs = Invoke-RestMethod -Uri "$Base/api/v1/admin/devices" -Headers $ah
$recent = @($devs | Sort-Object { $_.lastSyncAt } -Descending | Select-Object -First 5)
$synced = $recent | Where-Object { $_.lastRuleVersion -ge $latest.version -or $_.lastRuleVersion -eq $latest.version }
if ($synced) {
  Add-R "O1-heartbeat" "PASS" ("uuid={0} lastRuleVersion={1} callScreening={2} dns={3}" -f $synced[0].deviceUuid, $synced[0].lastRuleVersion, $synced[0].callScreeningEnabled, $synced[0].dnsConfigured)
  $DeviceUuid = $synced[0].deviceUuid
} elseif ($recent.Count -gt 0) {
  Add-R "O1-heartbeat" "WARN" ("device seen but version lag: " + (($recent | Select-Object -First 1 | ConvertTo-Json -Compress)))
  $DeviceUuid = $recent[0].deviceUuid
} else {
  Add-R "O1-heartbeat" "FAIL" "no devices after provision/sync"
  $DeviceUuid = $null
}

$holders = (& $Adb -s $Emu shell cmd role get-role-holders android.app.role.CALL_SCREENING 2>$null) -join ""
if ($holders -match $Pkg) { Add-R "O1-role" "PASS" "holder=$Pkg" } else { Add-R "O1-role" "WARN" "holder=$holders" }

function Invoke-EmuCall([string]$Number) {
  foreach ($n in @("+8613999887766","+821098765432","+12025550123","+447911123456","+61412345678","+818012345678","+79001234567")) {
    & $Adb -s $Emu emu gsm cancel $n 2>$null | Out-Null
  }
  Start-Sleep -Seconds 1
  & $Adb -s $Emu logcat -c 2>$null | Out-Null
  & $Adb -s $Emu emu gsm call $Number 2>$null | Out-Null
  Start-Sleep -Seconds 4
  $line = (& $Adb -s $Emu shell dumpsys telecom 2>$null | Select-String "SCREENING_COMPLETED" | Select-Object -Last 1)
  $log = (& $Adb -s $Emu logcat -d -s ElderCallScreen:I 2>$null | Select-Object -Last 3) -join " | "
  & $Adb -s $Emu emu gsm cancel $Number 2>$null | Out-Null
  $decision = if ($line -and $line.Line -match "Reject") { "Reject" } elseif ($line -and $line.Line -match "Allow") { "Allow" } else { "Unknown" }
  return [pscustomobject]@{ decision = $decision; telecom = if ($line) { $line.Line } else { "" }; log = $log }
}

function Expect-Call([string]$Id, [string]$Number, [string]$Expect, [string]$Why) {
  $r = Invoke-EmuCall $Number
  $ok = $r.decision -eq $Expect
  $status = if ($ok) { "PASS" } else { "FAIL" }
  Add-R $Id $status ("expect={0} got={1} num={2} why={3} log={4}" -f $Expect, $r.decision, $Number, $Why, $r.log.Substring(0, [Math]::Min(120, $r.log.Length)))
}

# Call matrix against ops GLOBALISM (call in applyTo)
$hasCall = $apply -contains "call"
if ($hasCall) {
  # Covered by Android calling-code map
  if ($allCountries -contains "CN") { Expect-Call "C-cn-block" "+8613999887766" "Reject" "CN in ops + in Android map" }
  else { Add-R "C-cn-block" "SKIP" "CN not in ops restriction" }

  if ($allCountries -contains "IR") { Expect-Call "C-ir-block" "+989121234567" "Reject" "IR in ops + in Android map" }
  else { Add-R "C-ir-block" "SKIP" "IR not restricted" }

  if ($allCountries -contains "KP") { Expect-Call "C-kp-block" "+85021234567" "Reject" "KP in ops + in Android map" }
  else { Add-R "C-kp-block" "SKIP" "KP not restricted" }

  # Not restricted / should allow
  if ($allCountries -notcontains "KR") { Expect-Call "C-kr-allow" "+821098765432" "Allow" "KR not in ops countries" }
  else { Expect-Call "C-kr-block" "+821098765432" "Reject" "KR unexpectedly restricted" }

  if ($allCountries -notcontains "US") { Expect-Call "C-us-allow" "+12025550123" "Allow" "US not in ops countries" }
  else { Expect-Call "C-us-block" "+12025550123" "Reject" "US restricted" }

  if ($allCountries -notcontains "JP") { Expect-Call "C-jp-allow" "+818012345678" "Allow" "JP not in ops countries" }
  else { Expect-Call "C-jp-block" "+818012345678" "Reject" "JP restricted" }

  # Ops-restricted but NOT in Android DEFAULT_CALLING_CODES → product gap (expect Allow today)
  if ($allCountries -contains "GB") {
    $r = Invoke-EmuCall "+447911123456"
    if ($r.decision -eq "Reject") {
      Add-R "C-gb-gap" "PASS" "GB blocked (calling-code map includes GB now)"
    } elseif ($r.decision -eq "Allow") {
      Add-R "C-gb-gap" "BUG" ("GB is in ops restriction but call Allowed — Android DEFAULT_CALLING_CODES lacks GB/+44. telecom=" + $r.decision)
    } else {
      Add-R "C-gb-gap" "WARN" ("ambiguous " + $r.decision)
    }
  }
  if ($allCountries -contains "AU") {
    $r = Invoke-EmuCall "+61412345678"
    if ($r.decision -eq "Reject") { Add-R "C-au-gap" "PASS" "AU blocked" }
    elseif ($r.decision -eq "Allow") { Add-R "C-au-gap" "BUG" "AU restricted in ops but Allowed — missing +61 in Android calling-code map" }
    else { Add-R "C-au-gap" "WARN" $r.decision }
  }
  if ($allCountries -contains "DE") {
    $r = Invoke-EmuCall "+4915112345678"
    if ($r.decision -eq "Reject") { Add-R "C-de-gap" "PASS" "DE blocked" }
    elseif ($r.decision -eq "Allow") { Add-R "C-de-gap" "BUG" "DE restricted in ops but Allowed — missing +49 in Android calling-code map" }
    else { Add-R "C-de-gap" "WARN" $r.decision }
  }
} else {
  Add-R "C-matrix" "SKIP" "ops applyTo has no call"
}

# Attacker fixture scan against Railway
if (Test-Path $AttackerApk) {
  & $Adb -s $Emu install -r $AttackerApk 2>&1 | Out-Null
  & $Adb -s $Emu shell am force-stop $Pkg
  & $Adb -s $Emu shell am start -n "$Pkg/.ui.MainActivity" | Out-Null
  Start-Sleep -Seconds 2
  & $Adb -s $Emu shell uiautomator dump /sdcard/ui.xml 2>$null | Out-Null
  $xml2 = (& $Adb -s $Emu shell cat /sdcard/ui.xml 2>$null) -join ""
  if ($xml2 -match 'resource-id="com.eldershield:id/saveProvision"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"') {
    $cx = [int](([int]$Matches[1] + [int]$Matches[3]) / 2)
    $cy = [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
    & $Adb -s $Emu shell input tap $cx $cy
  }
  Start-Sleep -Seconds 22
  $found = $false
  if ($DeviceUuid) {
    $detail = Invoke-RestMethod -Uri "$Base/api/v1/admin/devices/$DeviceUuid" -Headers $ah
    $hit = @($detail.scans | Where-Object { $_.packageName -eq $AttackerPkg })
    if ($hit.Count -gt 0) {
      $found = $true
      Add-R "A-scan-collect" "PASS" ("score={0} perms={1} reasons={2}" -f $hit[0].riskScore, (($hit[0].dangerousPermissions) -join '|'), (($hit[0].reasons) -join '|'))
    }
  }
  if (-not $found) {
    # scan all recent devices
    foreach ($d in $recent) {
      $detail = Invoke-RestMethod -Uri "$Base/api/v1/admin/devices/$($d.deviceUuid)" -Headers $ah
      $hit = @($detail.scans | Where-Object { $_.packageName -eq $AttackerPkg })
      if ($hit.Count -gt 0) {
        $found = $true
        Add-R "A-scan-collect" "PASS" ("via={0} score={1}" -f $d.deviceUuid, $hit[0].riskScore)
        break
      }
    }
  }
  if (-not $found) { Add-R "A-scan-collect" "WARN" "fixture installed but scan not yet on admin (worker timing)" }
} else {
  Add-R "A-scan-collect" "SKIP" "attacker apk missing"
}

# DNS / internet path (server denylist from ops)
$hasDns = ($apply -contains "dns") -or ($apply -contains "internet")
if ($hasDns) {
  if (@($den.tlds).Count -ge 50) { Add-R "D-denylist-size" "PASS" ("tlds={0} domains={1}" -f @($den.tlds).Count, $den.count) }
  else { Add-R "D-denylist-size" "WARN" ("unexpectedly small denylist tlds={0}" -f @($den.tlds).Count) }
  if ($allCountries -contains "CN" -and ($den.tlds -contains "cn")) { Add-R "D-cn-tld" "PASS" "cn in denylist tlds" }
  elseif ($allCountries -contains "CN") { Add-R "D-cn-tld" "FAIL" "CN restricted for dns/internet but cn tld missing" }
  if ($allCountries -contains "GB" -and (($den.tlds -contains "uk") -or ($den.tlds -contains "gb"))) {
    Add-R "D-gb-tld" "PASS" "GB maps to uk/gb in denylist"
  } elseif ($allCountries -contains "GB") {
    Add-R "D-gb-tld" "BUG" "GB restricted for dns but neither uk nor gb in denylist tlds"
  }
  # NextDNS sync probe
  try {
    $sync = Invoke-WebRequest -Uri "$Base/api/v1/admin/dns-denylist/sync-nextdns" -Headers $ah -Method POST -UseBasicParsing
    Add-R "D-nextdns-sync" $(if ($sync.StatusCode -eq 200) { "PASS" } else { "WARN" }) ("status={0}" -f $sync.StatusCode)
  } catch {
    $code = $null
    if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
    if ($code -eq 503) { Add-R "D-nextdns-sync" "SKIP" "NEXTDNS_* unset on Railway" }
    else { Add-R "D-nextdns-sync" "WARN" ("sync failed code={0} {1}" -f $code, $_.Exception.Message) }
  }
} else {
  Add-R "D-matrix" "SKIP" "ops applyTo has no dns/internet"
}

# Bundle size / crash smoke: dumpsys after large sync
$crash = (& $Adb -s $Emu logcat -d 2>$null | Select-String -Pattern "FATAL EXCEPTION|AndroidRuntime" | Select-Object -Last 3) -join " | "
if ($crash -match "com.eldershield") { Add-R "S-crash" "FAIL" $crash }
else { Add-R "S-crash" "PASS" "no ElderShield FATAL in recent logcat" }

$payload = @{
  ranAt = (Get-Date).ToUniversalTime().ToString("o")
  baseUrl = $Base
  emu = $Emu
  ops = @{
    countries = $allCountries.Count
    applyTo = @($apply)
    rulesVersion = $latest.version
    androidMapHits = $covered
    androidMapMissesSample = @($uncovered | Select-Object -First 30)
  }
  results = $Results
  summary = @{
    pass = @($Results | Where-Object status -eq PASS).Count
    fail = @($Results | Where-Object status -eq FAIL).Count
    bug = @($Results | Where-Object status -eq BUG).Count
    warn = @($Results | Where-Object status -eq WARN).Count
    skip = @($Results | Where-Object status -eq SKIP).Count
    info = @($Results | Where-Object status -eq INFO).Count
  }
}
$payload | ConvertTo-Json -Depth 8 | Set-Content $OutPath -Encoding UTF8
Write-Host "`n=== Summary ==="
$Results | Format-Table id, status, notes -Wrap
Write-Host "Wrote $OutPath"
$bad = @($Results | Where-Object { $_.status -in @("FAIL","BUG") }).Count
exit $(if ($bad -gt 0) { 1 } else { 0 })
.lastRuleVersion -eq $latest.version }
if ($synced) {
  Add-R "O1-heartbeat" "PASS" ("uuid={0} lastRuleVersion={1} callScreening={2} dns={3}" -f $synced[0].deviceUuid, $synced[0].lastRuleVersion, $synced[0].callScreeningEnabled, $synced[0].dnsConfigured)
  $DeviceUuid = $synced[0].deviceUuid
} elseif ($recent.Count -gt 0) {
  Add-R "O1-heartbeat" "WARN" ("device seen but version lag: " + (($recent | Select-Object -First 1 | ConvertTo-Json -Compress)))
  $DeviceUuid = $recent[0].deviceUuid
} else {
  Add-R "O1-heartbeat" "FAIL" "no devices after provision/sync"
  $DeviceUuid = $null
}

$holders = (& $Adb -s $Emu shell cmd role get-role-holders android.app.role.CALL_SCREENING 2>$null) -join ""
if ($holders -match $Pkg) { Add-R "O1-role" "PASS" "holder=$Pkg" } else { Add-R "O1-role" "WARN" "holder=$holders" }

function Invoke-EmuCall([string]$Number) {
  foreach ($n in @("+8613999887766","+821098765432","+12025550123","+447911123456","+61412345678","+818012345678","+79001234567")) {
    & $Adb -s $Emu emu gsm cancel $n 2>$null | Out-Null
  }
  Start-Sleep -Seconds 1
  & $Adb -s $Emu logcat -c 2>$null | Out-Null
  & $Adb -s $Emu emu gsm call $Number 2>$null | Out-Null
  Start-Sleep -Seconds 4
  $line = (& $Adb -s $Emu shell dumpsys telecom 2>$null | Select-String "SCREENING_COMPLETED" | Select-Object -Last 1)
  $log = (& $Adb -s $Emu logcat -d -s ElderCallScreen:I 2>$null | Select-Object -Last 3) -join " | "
  & $Adb -s $Emu emu gsm cancel $Number 2>$null | Out-Null
  $decision = if ($line -and $line.Line -match "Reject") { "Reject" } elseif ($line -and $line.Line -match "Allow") { "Allow" } else { "Unknown" }
  return [pscustomobject]@{ decision = $decision; telecom = if ($line) { $line.Line } else { "" }; log = $log }
}

function Expect-Call([string]$Id, [string]$Number, [string]$Expect, [string]$Why) {
  $r = Invoke-EmuCall $Number
  $ok = $r.decision -eq $Expect
  $status = if ($ok) { "PASS" } else { "FAIL" }
  Add-R $Id $status ("expect={0} got={1} num={2} why={3} log={4}" -f $Expect, $r.decision, $Number, $Why, $r.log.Substring(0, [Math]::Min(120, $r.log.Length)))
}

# Call matrix against ops GLOBALISM (call in applyTo)
$hasCall = $apply -contains "call"
if ($hasCall) {
  # Covered by Android calling-code map
  if ($allCountries -contains "CN") { Expect-Call "C-cn-block" "+8613999887766" "Reject" "CN in ops + in Android map" }
  else { Add-R "C-cn-block" "SKIP" "CN not in ops restriction" }

  if ($allCountries -contains "IR") { Expect-Call "C-ir-block" "+989121234567" "Reject" "IR in ops + in Android map" }
  else { Add-R "C-ir-block" "SKIP" "IR not restricted" }

  if ($allCountries -contains "KP") { Expect-Call "C-kp-block" "+85021234567" "Reject" "KP in ops + in Android map" }
  else { Add-R "C-kp-block" "SKIP" "KP not restricted" }

  # Not restricted / should allow
  if ($allCountries -notcontains "KR") { Expect-Call "C-kr-allow" "+821098765432" "Allow" "KR not in ops countries" }
  else { Expect-Call "C-kr-block" "+821098765432" "Reject" "KR unexpectedly restricted" }

  if ($allCountries -notcontains "US") { Expect-Call "C-us-allow" "+12025550123" "Allow" "US not in ops countries" }
  else { Expect-Call "C-us-block" "+12025550123" "Reject" "US restricted" }

  if ($allCountries -notcontains "JP") { Expect-Call "C-jp-allow" "+818012345678" "Allow" "JP not in ops countries" }
  else { Expect-Call "C-jp-block" "+818012345678" "Reject" "JP restricted" }

  # Ops-restricted but NOT in Android DEFAULT_CALLING_CODES → product gap (expect Allow today)
  if ($allCountries -contains "GB") {
    $r = Invoke-EmuCall "+447911123456"
    if ($r.decision -eq "Reject") {
      Add-R "C-gb-gap" "PASS" "GB blocked (calling-code map includes GB now)"
    } elseif ($r.decision -eq "Allow") {
      Add-R "C-gb-gap" "BUG" ("GB is in ops restriction but call Allowed — Android DEFAULT_CALLING_CODES lacks GB/+44. telecom=" + $r.decision)
    } else {
      Add-R "C-gb-gap" "WARN" ("ambiguous " + $r.decision)
    }
  }
  if ($allCountries -contains "AU") {
    $r = Invoke-EmuCall "+61412345678"
    if ($r.decision -eq "Reject") { Add-R "C-au-gap" "PASS" "AU blocked" }
    elseif ($r.decision -eq "Allow") { Add-R "C-au-gap" "BUG" "AU restricted in ops but Allowed — missing +61 in Android calling-code map" }
    else { Add-R "C-au-gap" "WARN" $r.decision }
  }
  if ($allCountries -contains "DE") {
    $r = Invoke-EmuCall "+4915112345678"
    if ($r.decision -eq "Reject") { Add-R "C-de-gap" "PASS" "DE blocked" }
    elseif ($r.decision -eq "Allow") { Add-R "C-de-gap" "BUG" "DE restricted in ops but Allowed — missing +49 in Android calling-code map" }
    else { Add-R "C-de-gap" "WARN" $r.decision }
  }
} else {
  Add-R "C-matrix" "SKIP" "ops applyTo has no call"
}

# Attacker fixture scan against Railway
if (Test-Path $AttackerApk) {
  & $Adb -s $Emu install -r $AttackerApk 2>&1 | Out-Null
  & $Adb -s $Emu shell am force-stop $Pkg
  & $Adb -s $Emu shell am start -n "$Pkg/.ui.MainActivity" | Out-Null
  Start-Sleep -Seconds 2
  & $Adb -s $Emu shell uiautomator dump /sdcard/ui.xml 2>$null | Out-Null
  $xml2 = (& $Adb -s $Emu shell cat /sdcard/ui.xml 2>$null) -join ""
  if ($xml2 -match 'resource-id="com.eldershield:id/saveProvision"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"') {
    $cx = [int](([int]$Matches[1] + [int]$Matches[3]) / 2)
    $cy = [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
    & $Adb -s $Emu shell input tap $cx $cy
  }
  Start-Sleep -Seconds 22
  $found = $false
  if ($DeviceUuid) {
    $detail = Invoke-RestMethod -Uri "$Base/api/v1/admin/devices/$DeviceUuid" -Headers $ah
    $hit = @($detail.scans | Where-Object { $_.packageName -eq $AttackerPkg })
    if ($hit.Count -gt 0) {
      $found = $true
      Add-R "A-scan-collect" "PASS" ("score={0} perms={1} reasons={2}" -f $hit[0].riskScore, (($hit[0].dangerousPermissions) -join '|'), (($hit[0].reasons) -join '|'))
    }
  }
  if (-not $found) {
    # scan all recent devices
    foreach ($d in $recent) {
      $detail = Invoke-RestMethod -Uri "$Base/api/v1/admin/devices/$($d.deviceUuid)" -Headers $ah
      $hit = @($detail.scans | Where-Object { $_.packageName -eq $AttackerPkg })
      if ($hit.Count -gt 0) {
        $found = $true
        Add-R "A-scan-collect" "PASS" ("via={0} score={1}" -f $d.deviceUuid, $hit[0].riskScore)
        break
      }
    }
  }
  if (-not $found) { Add-R "A-scan-collect" "WARN" "fixture installed but scan not yet on admin (worker timing)" }
} else {
  Add-R "A-scan-collect" "SKIP" "attacker apk missing"
}

# DNS / internet path (server denylist from ops)
$hasDns = ($apply -contains "dns") -or ($apply -contains "internet")
if ($hasDns) {
  if (@($den.tlds).Count -ge 50) { Add-R "D-denylist-size" "PASS" ("tlds={0} domains={1}" -f @($den.tlds).Count, $den.count) }
  else { Add-R "D-denylist-size" "WARN" ("unexpectedly small denylist tlds={0}" -f @($den.tlds).Count) }
  if ($allCountries -contains "CN" -and ($den.tlds -contains "cn")) { Add-R "D-cn-tld" "PASS" "cn in denylist tlds" }
  elseif ($allCountries -contains "CN") { Add-R "D-cn-tld" "FAIL" "CN restricted for dns/internet but cn tld missing" }
  if ($allCountries -contains "GB" -and (($den.tlds -contains "uk") -or ($den.tlds -contains "gb"))) {
    Add-R "D-gb-tld" "PASS" "GB maps to uk/gb in denylist"
  } elseif ($allCountries -contains "GB") {
    Add-R "D-gb-tld" "BUG" "GB restricted for dns but neither uk nor gb in denylist tlds"
  }
  # NextDNS sync probe
  try {
    $sync = Invoke-WebRequest -Uri "$Base/api/v1/admin/dns-denylist/sync-nextdns" -Headers $ah -Method POST -UseBasicParsing
    Add-R "D-nextdns-sync" $(if ($sync.StatusCode -eq 200) { "PASS" } else { "WARN" }) ("status={0}" -f $sync.StatusCode)
  } catch {
    $code = $null
    if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
    if ($code -eq 503) { Add-R "D-nextdns-sync" "SKIP" "NEXTDNS_* unset on Railway" }
    else { Add-R "D-nextdns-sync" "WARN" ("sync failed code={0} {1}" -f $code, $_.Exception.Message) }
  }
} else {
  Add-R "D-matrix" "SKIP" "ops applyTo has no dns/internet"
}

# Bundle size / crash smoke: dumpsys after large sync
$crash = (& $Adb -s $Emu logcat -d 2>$null | Select-String -Pattern "FATAL EXCEPTION|AndroidRuntime" | Select-Object -Last 3) -join " | "
if ($crash -match "com.eldershield") { Add-R "S-crash" "FAIL" $crash }
else { Add-R "S-crash" "PASS" "no ElderShield FATAL in recent logcat" }

$payload = @{
  ranAt = (Get-Date).ToUniversalTime().ToString("o")
  baseUrl = $Base
  emu = $Emu
  ops = @{
    countries = $allCountries.Count
    applyTo = @($apply)
    rulesVersion = $latest.version
    androidMapHits = $covered
    androidMapMissesSample = @($uncovered | Select-Object -First 30)
  }
  results = $Results
  summary = @{
    pass = @($Results | Where-Object status -eq PASS).Count
    fail = @($Results | Where-Object status -eq FAIL).Count
    bug = @($Results | Where-Object status -eq BUG).Count
    warn = @($Results | Where-Object status -eq WARN).Count
    skip = @($Results | Where-Object status -eq SKIP).Count
    info = @($Results | Where-Object status -eq INFO).Count
  }
}
$payload | ConvertTo-Json -Depth 8 | Set-Content $OutPath -Encoding UTF8
Write-Host "`n=== Summary ==="
$Results | Format-Table id, status, notes -Wrap
Write-Host "Wrote $OutPath"
$bad = @($Results | Where-Object { $_.status -in @("FAIL","BUG") }).Count
exit $(if ($bad -gt 0) { 1 } else { 0 })

