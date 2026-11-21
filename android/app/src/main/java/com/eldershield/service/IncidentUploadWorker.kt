package com.eldershield.service

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.Data
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.eldershield.data.local.CallEvidenceEntity
import com.eldershield.data.local.ElderShieldDatabase
import com.eldershield.data.remote.IncidentApi
import com.eldershield.domain.incident.AppForensicsSnapshot
import com.eldershield.domain.incident.CallEvidenceSnapshot
import com.eldershield.domain.incident.IncidentAssembler
import com.eldershield.domain.incident.ProtectionSnapshot
import com.eldershield.monitor.PrivateDnsMonitor
import com.eldershield.scanner.ApkForensics
import java.util.UUID

/** Upload A+B incident meta. Never logs phone numbers. */
class IncidentUploadWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result {
        val trigger = inputData.getString(KEY_TRIGGER).orEmpty()
        if (trigger.isBlank()) {
            return Result.failure()
        }
        return try {
            val prefs = applicationContext.getSharedPreferences(RuleSyncWorker.PREFS, Context.MODE_PRIVATE)
            val baseUrl = prefs.getString("base_url", RuleSyncWorker.DEFAULT_BASE_URL)
                ?: RuleSyncWorker.DEFAULT_BASE_URL
            val apiKey = prefs.getString("device_api_key", null).orEmpty()
            if (apiKey.isBlank()) {
                return Result.retry()
            }
            var deviceUuid = prefs.getString("device_uuid", null)
            if (deviceUuid.isNullOrBlank()) {
                deviceUuid = UUID.randomUUID().toString()
                prefs.edit().putString("device_uuid", deviceUuid).apply()
            }

            val nowMs = System.currentTimeMillis()
            val fromMs = nowMs - IncidentAssembler.WINDOW_PAST_MS
            val toMs = nowMs + IncidentAssembler.WINDOW_FUTURE_MS
            val db = ElderShieldDatabase.get(applicationContext)
            val callRows = db.callEvidenceDao().listBetween(fromMs, toMs)
            val calls = callRows.map { it.toSnapshot() }
            val apps = appsFromInput()

            val dns = PrivateDnsMonitor(applicationContext).read()
            val screening = CallScreeningRoleProbe.probe(applicationContext)
            val lastRuleVersion = db.ruleBundleDao().get()?.version ?: 0
            val lastSyncOk = prefs.getBoolean(RuleSyncWorker.PREF_LAST_SYNC_OK, true)
            val protection =
                ProtectionSnapshot(
                    dnsConfigured = dns.configured,
                    dnsHostClass = dns.hostClass,
                    callScreeningEnabled = screening.heldByUs,
                    lastRuleVersion = lastRuleVersion,
                    protectionDegraded = !dns.configured || !screening.heldByUs || !lastSyncOk,
                )

            val draft =
                IncidentAssembler.build(
                    incidentId = UUID.randomUUID().toString(),
                    deviceUuid = deviceUuid,
                    trigger = trigger,
                    nowMs = nowMs,
                    calls = calls,
                    apps = apps,
                    protection = protection,
                )
            IncidentApi(baseUrl, apiKey).post(draft)
            db.callEvidenceDao().trimToMax(200)
            Result.success()
        } catch (_: Exception) {
            Result.retry()
        }
    }

    private fun appsFromInput(): List<AppForensicsSnapshot> {
        val packageName = inputData.getString(KEY_PACKAGE)?.takeIf { it.isNotBlank() } ?: return emptyList()
        val f = ApkForensics.from(applicationContext.packageManager, packageName) ?: return emptyList()
        return listOf(
            AppForensicsSnapshot(
                packageName = f.packageName,
                signingCertSha256 = f.signingCertSha256,
                apkSha256 = f.apkSha256,
                versionName = f.versionName,
                versionCode = f.versionCode,
                installer = f.installer,
                permissions = f.permissions,
                reasons = emptyList(),
                riskScore = 0,
                firstSeenAtEpochMs = null,
            ),
        )
    }

    private fun CallEvidenceEntity.toSnapshot(): CallEvidenceSnapshot =
        CallEvidenceSnapshot(
            atEpochMs = atEpochMs,
            countryIso = countryIso,
            decision = decision,
            phoneHash = phoneHash,
            last4 = last4,
        )

    companion object {
        const val UNIQUE_NAME = "eldershield-incident-upload"
        const val KEY_TRIGGER = "trigger"
        const val KEY_PACKAGE = "package"

        fun enqueue(
            context: Context,
            trigger: String,
            packageName: String? = null,
        ) {
            val data =
                Data.Builder()
                    .putString(KEY_TRIGGER, trigger)
                    .apply {
                        if (!packageName.isNullOrBlank()) {
                            putString(KEY_PACKAGE, packageName)
                        }
                    }
                    .build()
            val request =
                OneTimeWorkRequestBuilder<IncidentUploadWorker>()
                    .setInputData(data)
                    .build()
            WorkManager.getInstance(context).enqueueUniqueWork(
                UNIQUE_NAME,
                ExistingWorkPolicy.APPEND_OR_REPLACE,
                request,
            )
        }
    }
}
