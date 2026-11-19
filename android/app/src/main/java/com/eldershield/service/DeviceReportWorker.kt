package com.eldershield.service

import android.content.Context
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
            val apiKey = prefs.getString("device_api_key", null).orEmpty()
            if (apiKey.isBlank()) {
                return Result.retry()
            }
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

            val screening = CallScreeningRoleProbe.probe(applicationContext)
            val api = DeviceApi(baseUrl, apiKey)
            api.postHeartbeat(
                deviceUuid = deviceUuid,
                appVersion = appVersion,
                dnsConfigured = dns.configured,
                callScreeningEnabled = screening.heldByUs,
                callScreeningHeldBy = screening.heldBy,
                callScreeningPeers = screening.peers,
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

    companion object {
        const val UNIQUE_NAME = "eldershield-device-report"
    }
}
