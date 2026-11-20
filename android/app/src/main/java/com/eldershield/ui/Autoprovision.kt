package com.eldershield.ui

import android.content.Context
import android.os.Build
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import com.eldershield.BuildConfig
import com.eldershield.data.ProvisionStore
import com.eldershield.data.remote.EnrollClient
import com.eldershield.data.remote.EnrollException
import com.eldershield.service.DeviceReportWorker
import com.eldershield.service.RuleSyncWorker
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Release path: BASE_URL from BuildConfig → enroll (Integrity token optional in debug) →
 * EncryptedPrefs token → silent WorkManager sync. No parent typing.
 */
object Autoprovision {
    sealed class Outcome {
        data object AlreadyProvisioned : Outcome()

        data object Enrolled : Outcome()

        data class Failed(val reason: String) : Outcome()
    }

    suspend fun ensure(
        context: Context,
        integrityToken: String? = null,
        integrityNonce: String? = null,
    ): Outcome =
        withContext(Dispatchers.IO) {
            val store = ProvisionStore(context)
            if (store.hasToken()) {
                enqueueWork(context)
                return@withContext Outcome.AlreadyProvisioned
            }
            val baseUrl =
                BuildConfig.BASE_URL.trim().trimEnd('/').ifBlank {
                    // Debug lab may still use reverse-forwarded localhost via manual prefs.
                    if (BuildConfig.DEBUG) {
                        store.baseUrl().takeIf { it != RuleSyncWorker.DEFAULT_BASE_URL }.orEmpty()
                    } else {
                        ""
                    }
                }
            if (baseUrl.isBlank() || baseUrl == RuleSyncWorker.DEFAULT_BASE_URL) {
                return@withContext Outcome.Failed("base_url_missing")
            }
            try {
                val result =
                    EnrollClient(baseUrl).enroll(
                        integrityToken = integrityToken,
                        integrityNonce = integrityNonce,
                        appVersion = BuildConfig.VERSION_NAME,
                        model = Build.MODEL,
                    )
                store.saveEnrollment(baseUrl, result.deviceUuid, result.deviceToken)
                enqueueWork(context)
                Outcome.Enrolled
            } catch (e: EnrollException) {
                Outcome.Failed("enroll_http_${e.httpCode}:${e.message}")
            } catch (e: Exception) {
                Outcome.Failed(e.message ?: "enroll_failed")
            }
        }

    fun enqueueWork(context: Context) {
        val wm = WorkManager.getInstance(context)
        wm.enqueueUniqueWork(
            "${RuleSyncWorker.UNIQUE_NAME}-now",
            ExistingWorkPolicy.REPLACE,
            OneTimeWorkRequestBuilder<RuleSyncWorker>().build(),
        )
        wm.enqueueUniqueWork(
            "${DeviceReportWorker.UNIQUE_NAME}-now",
            ExistingWorkPolicy.REPLACE,
            OneTimeWorkRequestBuilder<DeviceReportWorker>().build(),
        )
    }
}
