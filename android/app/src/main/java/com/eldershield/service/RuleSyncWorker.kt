package com.eldershield.service

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.eldershield.data.ActiveRuleBundleCache
import com.eldershield.data.RuleRepositoryImpl
import com.eldershield.data.local.ElderShieldDatabase
import com.eldershield.data.remote.RulesApi
import com.eldershield.domain.sync.RuleSyncPolicy
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
        return try {
            val prefs = applicationContext.getSharedPreferences("eldershield", Context.MODE_PRIVATE)
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
            ActiveRuleBundleCache.bundle = policy.activeBundle(outcome)
            if (SyncWorkDisposition.shouldRetry(outcome)) {
                Result.retry()
            } else {
                Result.success()
            }
        } catch (_: Exception) {
            // Never crash the process; retry later with backoff.
            Result.retry()
        }
    }

    companion object {
        const val UNIQUE_NAME = "eldershield-rule-sync"
        const val DEFAULT_BASE_URL = "https://example.invalid"
    }
}
