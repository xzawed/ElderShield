package com.eldershield

import android.app.Application
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.eldershield.service.DeviceReportWorker
import com.eldershield.service.RuleSyncWorker
import java.util.concurrent.TimeUnit

class ElderShieldApp : Application() {
    override fun onCreate() {
        super.onCreate()
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
        // Immediate attempt on process start (no-op retry if prefs not provisioned yet).
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
}
