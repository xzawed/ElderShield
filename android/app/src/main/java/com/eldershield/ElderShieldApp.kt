package com.eldershield

import android.app.Application
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.eldershield.service.RuleSyncWorker
import java.util.concurrent.TimeUnit

class ElderShieldApp : Application() {
    override fun onCreate() {
        super.onCreate()
        val request =
            PeriodicWorkRequestBuilder<RuleSyncWorker>(1, TimeUnit.HOURS)
                .build()
        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            RuleSyncWorker.UNIQUE_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            request,
        )
    }
}
