package com.eldershield

import android.app.Application
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.eldershield.data.ActiveRuleBundleCache
import com.eldershield.data.RuleBundleJson
import com.eldershield.data.local.ElderShieldDatabase
import com.eldershield.service.DeviceReportWorker
import com.eldershield.service.RuleSyncWorker
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import java.util.concurrent.TimeUnit

class ElderShieldApp : Application() {
    private val appScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onCreate() {
        super.onCreate()
        warmRuleCacheFromRoom()
        val wm = WorkManager.getInstance(this)
        wm.enqueueUniquePeriodicWork(
            RuleSyncWorker.UNIQUE_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            PeriodicWorkRequestBuilder<RuleSyncWorker>(1, TimeUnit.HOURS).build(),
        )
        wm.enqueueUniquePeriodicWork(
            DeviceReportWorker.UNIQUE_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            PeriodicWorkRequestBuilder<DeviceReportWorker>(6, TimeUnit.HOURS).build(),
        )
        wm.enqueueUniqueWork(
            "${RuleSyncWorker.UNIQUE_NAME}-boot",
            ExistingWorkPolicy.KEEP,
            OneTimeWorkRequestBuilder<RuleSyncWorker>().build(),
        )
        wm.enqueueUniqueWork(
            "${DeviceReportWorker.UNIQUE_NAME}-boot",
            ExistingWorkPolicy.KEEP,
            OneTimeWorkRequestBuilder<DeviceReportWorker>().build(),
        )
    }

    /** Prefill memory so CallScreening avoids Room runBlocking on first ring. */
    private fun warmRuleCacheFromRoom() {
        appScope.launch {
            runCatching {
                val entity = ElderShieldDatabase.get(this@ElderShieldApp).ruleBundleDao().get() ?: return@launch
                ActiveRuleBundleCache.publishIfNewer(RuleBundleJson.decode(entity.payloadJson))
            }
        }
    }
}
