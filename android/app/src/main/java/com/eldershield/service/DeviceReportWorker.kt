package com.eldershield.service

import android.app.role.RoleManager
import android.content.Context
import android.os.Build
import android.telecom.TelecomManager
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.eldershield.data.local.ElderShieldDatabase
import com.eldershield.data.remote.DeviceApi
import com.eldershield.monitor.PrivateDnsMonitor
import com.eldershield.scanner.PackageAppScanner
import java.util.UUID

/** Silent scan + DNS status + heartbeat. Never shows parent UI. */
class DeviceReportWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result {
        return try {
            val prefs = applicationContext.getSharedPreferences("eldershield", Context.MODE_PRIVATE)
            val baseUrl = prefs.getString("base_url", RuleSyncWorker.DEFAULT_BASE_URL) ?: RuleSyncWorker.DEFAULT_BASE_URL
            val apiKey = prefs.getString("device_api_key", RuleSyncWorker.DEFAULT_DEVICE_KEY) ?: RuleSyncWorker.DEFAULT_DEVICE_KEY
            var deviceUuid = prefs.getString("device_uuid", null)
            if (deviceUuid.isNullOrBlank()) {
                deviceUuid = UUID.randomUUID().toString()
                prefs.edit().putString("device_uuid", deviceUuid).apply()
            }

            val dns = PrivateDnsMonitor(applicationContext).read()
            val lastRuleVersion =
                ElderShieldDatabase.get(applicationContext).ruleBundleDao().get()?.version ?: 0
            val appVersion =
                applicationContext.packageManager
                    .getPackageInfo(applicationContext.packageName, 0)
                    .versionName ?: "0.1.0"

            val api = DeviceApi(baseUrl, apiKey)
            api.postHeartbeat(
                deviceUuid = deviceUuid,
                appVersion = appVersion,
                dnsConfigured = dns.configured,
                callScreeningEnabled = isCallScreeningEnabled(),
                lastRuleVersion = lastRuleVersion,
            )

            val suspicious = PackageAppScanner(applicationContext).scanSuspicious()
            if (suspicious.isNotEmpty()) {
                api.postScanResult(deviceUuid, suspicious)
            }
            Result.success()
        } catch (_: Exception) {
            Result.retry()
        }
    }

    private fun isCallScreeningEnabled(): Boolean {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val rm = applicationContext.getSystemService(RoleManager::class.java)
                rm?.isRoleHeld(RoleManager.ROLE_CALL_SCREENING) == true
            } else {
                val tm = applicationContext.getSystemService(TelecomManager::class.java)
                tm?.defaultDialerPackage == applicationContext.packageName
            }
        } catch (_: Exception) {
            false
        }
    }

    companion object {
        const val UNIQUE_NAME = "eldershield-device-report"
    }
}
