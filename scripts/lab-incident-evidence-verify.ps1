# Lab verify: synthetic incident POST + admin export (no raw phone).
# SAFETY: gsm call inject only on emulator-5554; never PSTN on USB phone.
# Usage: powershell -File scripts/lab-incident-evidence-verify.ps1
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
$Emu = "emulator-5554"
$Base = if ($env:ELDERSHIELD_LAB_URL) { $env:ELDERSHIELD_LAB_URL } else { "https://eldershield.up.railway.app" }
$KeysPath = if ($env:ELDERSHIELD_KEYS_JSON) { $env:ELDERSHIELD_KEYS_JSON } else { Join-Path $env:TEMP "es-keys.json" }
$DeviceUuid = "lab-incident-evidence-pack"
$Results = [System.Collections.Generic.List[object]]::new()
$fail = 0

function Add-R([string]$Id, [string]$Status, [string]$Notes) {
  $Results.Add([pscustomobject]@{ id = $Id; status = $Status; notes = "$Notes" })
  Write-Host ("[{0}] {1} - {2}" -f $Id, $Status, $Notes)
  if ($Status -eq "FAIL") { $script:fail++ }
}

function Online([string]$Serial) {
  if (-not (Test-Path $Adb)) { return $false }
  return [bool](& $Adb devices | Select-String ("^{0}\s+device" -f [regex]::Escape($Serial)))
}

function Assert-EmuGsmOnly {
  if ($Emu -notmatch '^emulator-5554$') {
    throw "gsm refused: only emulator-5554 is allowed"
  }
}

Write-Host "=== Incident evidence pack verify ==="
Write-Host "Base=$Base keys=$KeysPath emu=$(Online $Emu)"

if (-not (Test-Path $KeysPath)) {
  Add-R "K0-keys" "FAIL" "Missing keys JSON: $KeysPath"
  Write-Host "FAIL"
  exit 1
}
$keys = Get-Content $KeysPath -Raw | ConvertFrom-Json
$AdminKey = $keys.ADMIN_API_KEY
$DeviceKey = $keys.DEVICE_API_KEY
if (-not $AdminKey -or -not $DeviceKey) {
  Add-R "K0-keys" "FAIL" "ADMIN_API_KEY / DEVICE_API_KEY missing in keys JSON"
  Write-Host "FAIL"
  exit 1
}
Add-R "K0-keys" "PASS" "loaded (values not printed)"

$ah = @{ "X-API-Key" = $AdminKey }
$dh = @{ "X-API-Key" = $DeviceKey }

try {
  $health = Invoke-RestMethod -Uri "$Base/health" -TimeoutSec 20 -UseBasicParsing
  Add-R "H0-health" "PASS" ("bundleVersion={0}" -f $health.bundleVersion)
} catch {
  Add-R "H0-health" "FAIL" $_.Exception.Message
  Write-Host "FAIL"
  exit 1
}

# Heartbeat first so the lab device row exists (shared device key may mint).
$hbBody = @{
  deviceUuid = $DeviceUuid
  appVersion = "lab-incident-evidence"
  dnsConfigured = $true
  callScreeningEnabled = $true
  lastRuleVersion = 1
} | ConvertTo-Json -Compress
try {
  $hb = Invoke-WebRequest -Uri "$Base/api/v1/devices/heartbeat" -Headers $dh -Method POST -Body $hbBody -ContentType "application/json" -TimeoutSec 20 -UseBasicParsing
  if ($hb.StatusCode -ge 200 -and $hb.StatusCode -lt 300) {
    Add-R "H1-heartbeat" "PASS" ("deviceUuid={0} http={1}" -f $DeviceUuid, $hb.StatusCode)
  } else {
    Add-R "H1-heartbeat" "FAIL" ("http={0} {1}" -f $hb.StatusCode, $hb.Content)
    Write-Host "FAIL"
    exit 1
  }
} catch {
  Add-R "H1-heartbeat" "FAIL" $_.Exception.Message
  Write-Host "FAIL"
  exit 1
}

# Optional gsm: emulator-5554 only. Default path is synthetic POST (no PSTN).
if (Online $Emu) {
  Assert-EmuGsmOnly
  Add-R "G0-emu" "SKIP" "emulator-5554 online; gsm inject not required (synthetic POST is the evidence path)"
} else {
  Add-R "G0-emu" "SKIP" "emulator-5554 not connected; synthetic POST only"
}

$sha = [System.Security.Cryptography.SHA256]::Create()
$hashBytes = $sha.ComputeHash([Text.Encoding]::UTF8.GetBytes("lab-cn-reject-meta"))
$phoneHash = ([BitConverter]::ToString($hashBytes) -replace "-", "").ToLowerInvariant()
$incidentId = [guid]::NewGuid().ToString()
$triggeredAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$incBody = @{
  incidentId = $incidentId
  deviceUuid = $DeviceUuid
  triggeredAt = $triggeredAt
  triggers = @("call_reject")
  apps = @()
  calls = @(
    @{
      at = $triggeredAt
      countryIso = "CN"
      decision = "Reject"
      phoneHash = $phoneHash
    }
  )
  dns = @{ available = $false; events = @() }
} | ConvertTo-Json -Depth 6 -Compress

try {
  $post = Invoke-WebRequest -Uri "$Base/api/v1/devices/incidents" -Headers $dh -Method POST -Body $incBody -ContentType "application/json" -TimeoutSec 30 -UseBasicParsing
  if ($post.StatusCode -in 200, 201) {
    $posted = $post.Content | ConvertFrom-Json
    if ($posted.incidentId) { $incidentId = $posted.incidentId }
    Add-R "P1-post" "PASS" ("http={0} incidentId={1}" -f $post.StatusCode, $incidentId)
  } else {
    Add-R "P1-post" "FAIL" ("http={0} {1}" -f $post.StatusCode, $post.Content)
    Write-Host "FAIL"
    exit 1
  }
} catch {
  $code = $null
  if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
  Add-R "P1-post" "FAIL" ("POST {0}/api/v1/devices/incidents http={1} {2}" -f $Base, $code, $_.Exception.Message)
  Write-Host "FAIL"
  exit 1
}

try {
  $exp = Invoke-WebRequest -Uri "$Base/api/v1/admin/incidents/$incidentId/export" -Headers $ah -TimeoutSec 30 -UseBasicParsing
  $raw = [string]$exp.Content
  $hasPhoneNumber = $raw -match "phoneNumber"
  $hasPlus86 = $raw -match [regex]::Escape("+86")
  $hasHash = $raw -match [regex]::Escape($phoneHash)
  if ($exp.StatusCode -eq 200 -and -not $hasPhoneNumber -and -not $hasPlus86 -and $hasHash) {
    Add-R "E1-export" "PASS" "export has phoneHash; no phoneNumber; no +86"
  } else {
    $snip = if ($raw.Length -gt 240) { $raw.Substring(0, 240) } else { $raw }
    Add-R "E1-export" "FAIL" ("http={0} phoneNumber={1} +86={2} hash={3} snip={4}" -f $exp.StatusCode, $hasPhoneNumber, $hasPlus86, $hasHash, $snip)
  }
} catch {
  Add-R "E1-export" "FAIL" $_.Exception.Message
}

Write-Host ""
Write-Host "=== Summary ==="
$Results | Group-Object status | ForEach-Object { "{0}={1}" -f $_.Name, $_.Count }
if ($fail -gt 0) {
  Write-Host "FAIL"
  exit 1
}
Write-Host "PASS"
exit 0
