# ElderShield full lab verify orchestrator (host unit → AVD batch → USB nocall).
# Usage (from repo root):
#   powershell -File scripts/lab-full-verify.ps1
# Optional: ELDERSHIELD_S22_SERIAL, ELDERSHIELD_LAB_URL, skip flags
#   -SkipAvd / -SkipPhone / -SkipHost
# SAFETY: never issues ACTION.CALL / gsm on physical devices (delegates to existing scripts).
param(
  [switch]$SkipHost,
  [switch]$SkipAvd,
  [switch]$SkipPhone
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
$Py = Join-Path $Root "backend\.venv\Scripts\python.exe"
$Date = Get-Date -Format "yyyy-MM-dd"
$OutSuffix = if ($SkipHost -and $SkipAvd -and $SkipPhone) { "preflight" } else { "lab-full-verify" }
$OutPath = Join-Path $Root "docs\plans\$Date-$OutSuffix-results.json"
$Results = [System.Collections.Generic.List[object]]::new()

function Add-R([string]$Id, [string]$Status, [string]$Notes) {
  $Results.Add([pscustomobject]@{ id = $Id; status = $Status; notes = "$Notes"; at = (Get-Date).ToString("o") })
  Write-Host ("[{0}] {1} — {2}" -f $Id, $Status, $Notes)
}

function Load-DotEnv([string]$Path) {
  if (-not (Test-Path $Path)) { return }
  Get-Content $Path | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $i = $_.IndexOf('=')
    if ($i -lt 1) { return }
    $k = $_.Substring(0, $i).Trim()
    $v = $_.Substring($i + 1).Trim()
    # Do not clobber keys already set for this session (CI / caller override).
    $existing = [Environment]::GetEnvironmentVariable($k, "Process")
    if ([string]::IsNullOrEmpty($existing)) {
      Set-Item -Path "Env:$k" -Value $v
    }
  }
}

Load-DotEnv (Join-Path $Root "backend\.env")
$Base = if ($env:ELDERSHIELD_LAB_URL) { $env:ELDERSHIELD_LAB_URL } else { "http://127.0.0.1:8765" }
$env:ELDERSHIELD_LAB_URL = $Base

# Discover USB phone serial if not set (first non-emulator device).
if (-not $env:ELDERSHIELD_S22_SERIAL) {
  $lines = & $Adb devices | Where-Object { $_ -match '^\S+\s+device$' -and $_ -notmatch '^emulator-' }
  if ($lines) {
    $env:ELDERSHIELD_S22_SERIAL = (($lines | Select-Object -First 1) -split '\s+')[0]
  }
}
$Phone = $env:ELDERSHIELD_S22_SERIAL
$EmuOnline = [bool](& $Adb devices | Select-String '^emulator-\d+\s+device')
$PhoneOnline = if ($Phone) { [bool](& $Adb devices | Select-String ("^{0}\s+device" -f [regex]::Escape($Phone))) } else { $false }

Write-Host "=== ElderShield lab-full-verify ==="
Write-Host "Base=$Base emu=$EmuOnline phone=$Phone online=$PhoneOnline"

# --- Preflight ---
if (-not (Test-Path $Py)) {
  Add-R "preflight-venv" "FAIL" "backend .venv python missing"
} else {
  Add-R "preflight-venv" "PASS" "venv ok"
}
try {
  $h = Invoke-RestMethod -Uri "$Base/health" -TimeoutSec 10
  if ($h.status -eq "ok") { Add-R "preflight-health" "PASS" ("devices={0} bundle={1}" -f $h.devices, $h.bundleVersion) }
  else { Add-R "preflight-health" "FAIL" ($h | ConvertTo-Json -Compress) }
} catch {
  Add-R "preflight-health" "FAIL" $_.Exception.Message
}
if ([string]::IsNullOrEmpty($env:ADMIN_API_KEY) -or $env:ADMIN_API_KEY -match 'change-me') {
  Add-R "preflight-keys" "FAIL" "ADMIN_API_KEY missing or insecure default"
} elseif ([string]::IsNullOrEmpty($env:DEVICE_API_KEY) -or $env:DEVICE_API_KEY -match 'change-me') {
  Add-R "preflight-keys" "FAIL" "DEVICE_API_KEY missing or insecure default"
} else {
  Add-R "preflight-keys" "PASS" ("admin_len={0} device_len={1}" -f $env:ADMIN_API_KEY.Length, $env:DEVICE_API_KEY.Length)
}
Add-R "preflight-adb" $(if ($EmuOnline -or $PhoneOnline) { "PASS" } else { "WARN" }) ("emu={0} phone={1}" -f $EmuOnline, $(if ($PhoneOnline) { $Phone } else { "none" }))

$fatal = @($Results | Where-Object { $_.id -like "preflight-*" -and $_.status -eq "FAIL" }).Count
if ($fatal -gt 0) {
  $Results | ConvertTo-Json -Depth 5 | Set-Content -Path $OutPath -Encoding UTF8
  Write-Host "Abort: preflight FAIL. Wrote $OutPath"
  exit 1
}

# --- Host unit ---
if (-not $SkipHost) {
  Push-Location (Join-Path $Root "backend")
  $env:PYTHONPATH = (Join-Path $Root "backend")
  $pytestOut = & $Py -m pytest -q 2>&1 | Out-String
  $pytestCode = $LASTEXITCODE
  Pop-Location
  if ($pytestCode -eq 0) { Add-R "host-pytest" "PASS" ($pytestOut.Trim().Split("`n")[-1]) }
  else {
    Add-R "host-pytest" "FAIL" $pytestOut.Substring([Math]::Max(0, $pytestOut.Length - 500))
    $Results | ConvertTo-Json -Depth 5 | Set-Content -Path $OutPath -Encoding UTF8
    exit 1
  }

  Push-Location (Join-Path $Root "android")
  $gradleOut = & .\gradlew.bat :core:test :app:assembleDebug --no-daemon 2>&1 | Out-String
  $gradleCode = $LASTEXITCODE
  Pop-Location
  if ($gradleCode -eq 0) { Add-R "host-android" "PASS" ":core:test + assembleDebug" }
  else {
    Add-R "host-android" "FAIL" $gradleOut.Substring([Math]::Max(0, $gradleOut.Length - 500))
    $Results | ConvertTo-Json -Depth 5 | Set-Content -Path $OutPath -Encoding UTF8
    exit 1
  }
} else {
  Add-R "host-pytest" "SKIP" "-SkipHost"
  Add-R "host-android" "SKIP" "-SkipHost"
}

# --- AVD batch (includes S22 L3/L10 when serial set) ---
if (-not $SkipAvd) {
  if (-not $EmuOnline) {
    Add-R "avd-batch" "SKIP" "no emulator connected"
  } else {
    $batchLog = Join-Path $env:TEMP "es-lab-batch.log"
    & powershell -NoProfile -File (Join-Path $PSScriptRoot "lab-batch-verify.ps1") *>&1 | Tee-Object -FilePath $batchLog | Out-Null
    $batchCode = $LASTEXITCODE
    $batchJson = Join-Path $Root "docs\plans\2026-11-19-lab-batch-results.json"
    if (Test-Path $batchJson) {
      try {
        $batch = Get-Content $batchJson -Raw | ConvertFrom-Json
        $failN = @($batch | Where-Object { $_.status -eq "FAIL" }).Count
        $passN = @($batch | Where-Object { $_.status -eq "PASS" }).Count
        $status = if ($batchCode -eq 0 -and $failN -eq 0) { "PASS" } elseif ($failN -eq 0) { "WARN" } else { "FAIL" }
        Add-R "avd-batch" $status ("pass={0} fail={1} exit={2}" -f $passN, $failN, $batchCode)
        foreach ($row in $batch) {
          Add-R ("batch:" + $row.id) $row.status $row.notes
        }
      } catch {
        Add-R "avd-batch" "WARN" ("batch ran but JSON parse failed: " + $_.Exception.Message)
      }
    } else {
      Add-R "avd-batch" $(if ($batchCode -eq 0) { "WARN" } else { "FAIL" }) ("exit=$batchCode no results json")
    }
  }
} else {
  Add-R "avd-batch" "SKIP" "-SkipAvd"
}

# --- USB nocall (bank / DNS / BD) — only if phone online and not already covered enough ---
if (-not $SkipPhone) {
  if (-not $PhoneOnline) {
    Add-R "phone-nocall" "SKIP" "no USB phone (set ELDERSHIELD_S22_SERIAL)"
  } else {
    $nocallLog = Join-Path $env:TEMP "es-lab-nocall.log"
    & powershell -NoProfile -File (Join-Path $PSScriptRoot "lab-nocall-device-verify.ps1") *>&1 | Tee-Object -FilePath $nocallLog | Out-Null
    $nocallCode = $LASTEXITCODE
    $tail = ""
    if (Test-Path $nocallLog) {
      $tail = ((Get-Content $nocallLog -Tail 15) -join " | ")
    }
    if ($nocallCode -eq 0) { Add-R "phone-nocall" "PASS" $tail.Substring(0, [Math]::Min(300, $tail.Length)) }
    else { Add-R "phone-nocall" "FAIL" ("exit=$nocallCode " + $tail.Substring(0, [Math]::Min(300, $tail.Length))) }
  }
} else {
  Add-R "phone-nocall" "SKIP" "-SkipPhone"
}

$Results | ConvertTo-Json -Depth 5 | Set-Content -Path $OutPath -Encoding UTF8
Write-Host "`n=== Summary ==="
$Results | Where-Object { $_.id -notlike "batch:*" } | Format-Table id, status, notes -AutoSize
Write-Host "Wrote $OutPath"
$fail = @($Results | Where-Object { $_.status -eq "FAIL" -and $_.id -notlike "batch:*" }).Count
# Also fail if nested batch had FAIL
$batchFail = @($Results | Where-Object { $_.id -like "batch:*" -and $_.status -eq "FAIL" }).Count
exit $(if (($fail + $batchFail) -gt 0) { 1 } else { 0 })
