# Phase A acceptance: Admin SPA login, shell, session-gated admin API.
# Usage (repo root): powershell -File scripts/lab-admin-spa-smoke.ps1
# Optional: $env:ELDERSHIELD_LAB_URL, $env:ELDERSHIELD_KEYS_JSON
$ErrorActionPreference = "Continue"

$Base = if ($env:ELDERSHIELD_LAB_URL) { $env:ELDERSHIELD_LAB_URL } else { "https://eldershield.up.railway.app" }
$KeysPath = if ($env:ELDERSHIELD_KEYS_JSON) { $env:ELDERSHIELD_KEYS_JSON } else { Join-Path $env:TEMP "es-keys.json" }
$Results = [System.Collections.Generic.List[object]]::new()

function Add-R([string]$Id, [string]$Status, [string]$Notes) {
  $Results.Add([pscustomobject]@{ id = $Id; status = $Status; notes = $Notes })
  Write-Host ("[{0}] {1} — {2}" -f $Id, $Status, $Notes)
}

Write-Host "=== ElderShield lab-admin-spa-smoke ==="
Write-Host "Base=$Base Keys=$KeysPath"

if (-not (Test-Path $KeysPath)) {
  Add-R "preflight-keys" "FAIL" "missing keys json"
  Write-Host "FAIL: $($Results | Where-Object { $_.status -eq 'FAIL' } | Measure-Object | Select-Object -ExpandProperty Count) check(s)"
  exit 1
}

$keys = Get-Content $KeysPath -Raw | ConvertFrom-Json
$AdminKey = $keys.ADMIN_API_KEY
if ([string]::IsNullOrWhiteSpace($AdminKey)) {
  Add-R "preflight-keys" "FAIL" "ADMIN_API_KEY empty in keys json"
  Write-Host "FAIL: 1 check(s)"
  exit 1
}
Add-R "preflight-keys" "PASS" "admin key loaded"

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$loginBody = (@{ apiKey = $AdminKey } | ConvertTo-Json -Compress)

try {
  $login = Invoke-WebRequest -Uri "$Base/admin/ui/api/login" -Method POST `
    -Body $loginBody -ContentType "application/json; charset=utf-8" `
    -WebSession $session -TimeoutSec 30 -UseBasicParsing
  if ($login.StatusCode -eq 200 -and ($login.Content -match '"ok"\s*:\s*true')) {
    Add-R "login-json" "PASS" "session cookie set"
  } else {
    Add-R "login-json" "FAIL" ("status={0} body={1}" -f $login.StatusCode, $login.Content)
  }
} catch {
  Add-R "login-json" "FAIL" $_.Exception.Message
}

try {
  $shell = Invoke-WebRequest -Uri "$Base/admin/ui/" -WebSession $session -TimeoutSec 30 -UseBasicParsing
  $ct = $shell.Headers["Content-Type"]
  if ($shell.StatusCode -eq 200 -and $ct -match "html" -and $shell.Content -match 'id="root"') {
    Add-R "spa-shell" "PASS" "200 html root"
  } else {
    Add-R "spa-shell" "FAIL" ("status={0} ct={1}" -f $shell.StatusCode, $ct)
  }
} catch {
  Add-R "spa-shell" "FAIL" $_.Exception.Message
}

try {
  # Cookie auth requires SPA CSRF header (same as admin-web client.ts).
  $dev = Invoke-WebRequest -Uri "$Base/api/v1/admin/devices" -WebSession $session `
    -Headers @{ "X-ElderShield-Admin" = "1" } -TimeoutSec 30 -UseBasicParsing
  if ($dev.StatusCode -eq 200) {
    $parsed = $dev.Content | ConvertFrom-Json
    $n = if ($parsed -is [System.Array]) { $parsed.Count } else { 0 }
    Add-R "admin-devices-cookie" "PASS" ("200 list count={0}" -f $n)
  } else {
    Add-R "admin-devices-cookie" "FAIL" ("status={0}" -f $dev.StatusCode)
  }
} catch {
  Add-R "admin-devices-cookie" "FAIL" $_.Exception.Message
}

try {
  # Fresh session so prior -Headers are not reused (WebRequestSession keeps them).
  $csrfSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
  foreach ($c in $session.Cookies.GetCookies([uri]$Base)) {
    $csrfSession.Cookies.Add($c)
  }
  $null = Invoke-WebRequest -Uri "$Base/api/v1/admin/devices" -WebSession $csrfSession `
    -TimeoutSec 30 -UseBasicParsing
  Add-R "admin-devices-csrf" "FAIL" "expected 401 without CSRF header"
} catch {
  $code = $null
  try { $code = [int]$_.Exception.Response.StatusCode } catch {}
  if ($code -eq 401) {
    Add-R "admin-devices-csrf" "PASS" "cookie without header → 401"
  } else {
    Add-R "admin-devices-csrf" "FAIL" ("status={0} err={1}" -f $code, $_.Exception.Message)
  }
}

$fail = @($Results | Where-Object { $_.status -eq "FAIL" }).Count
$pass = @($Results | Where-Object { $_.status -eq "PASS" }).Count
Write-Host "---"
Write-Host ("SUMMARY: PASS={0} FAIL={1}" -f $pass, $fail)
if ($fail -gt 0) { exit 1 }
exit 0