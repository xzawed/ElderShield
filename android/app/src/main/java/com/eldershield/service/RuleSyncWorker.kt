package com.eldershield.service

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.eldershield.data.ActiveRuleBundleCache
import com.eldershield.data.RuleRepositoryImpl
import com.eldershield.data.local.ElderShieldDatabase
import com.eldershield.data.remote.RulesApi
import com.eldershield.domain.sync.RuleSyncPolicy
import com.eldershield.domain.sync.SyncErrorCodes
import com.eldershield.domain.sync.SyncOutcome
import com.eldershield.domain.sync.SyncWorkDisposition

/**
 * Silent background sync — never surfaces UI to the parent device.
 * Failures keep cache for screening (UT-A-32/33) but WorkManager retries.
 */
class RuleSyncWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result {
        val prefs = applicationContext.getSharedPreferences("eldershield", Context.MODE_PRIVATE)
        return try {
            val baseUrl = prefs.getString("base_url", DEFAULT_BASE_URL) ?: DEFAULT_BASE_URL
            val apiKey = prefs.getString("device_api_key", null).orEmpty()
            if (apiKey.isBlank()) {
                // No provisioned key — retry later; never fall back to insecure defaults.
                return Result.retry()
            }
            val dao = ElderShieldDatabase.get(applicationContext).ruleBundleDao()
            val repo = RuleRepositoryImpl(dao, RulesApi(baseUrl, apiKey))
            val policy = RuleSyncPolicy(repo)
            val outcome = policy.sync()
            ActiveRuleBundleCache.publishIfNewer(policy.activeBundle(outcome))
            prefs
                .edit()
                .putBoolean(PREF_LAST_SYNC_OK, true)
                .remove(PREF_LAST_SYNC_ERROR)
                .apply()
            if (SyncWorkDisposition.shouldRetry(outcome)) {
                Result.retry()
            } else {
                Result.success()
            }
        } catch (e: Exception) {
            val code =
                when {
                    e.message?.contains("HTTP 4") == true -> "http_4xx"
                    e.message?.contains("HTTP 5") == true -> "http_5xx"
                    else -> "network"
                }
            prefs
                .edit()
                .putBoolean(PREF_LAST_SYNC_OK, false)
                .putString(PREF_LAST_SYNC_ERROR, code)
                .apply()
            // Never crash the process; retry later with backoff.
            Result.retry()
        }
    }

    companion object {
        const val UNIQUE_NAME = "eldershield-rule-sync"
        const val DEFAULT_BASE_URL = "https://example.invalid"
        const val PREF_LAST_SYNC_OK = "last_sync_ok"
        const val PREF_LAST_SYNC_ERROR = "last_sync_error_code"
    }
}
