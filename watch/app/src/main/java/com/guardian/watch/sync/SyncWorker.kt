package com.guardian.watch.sync

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.guardian.watch.data.repository.SyncResult
import com.guardian.watch.graph
import java.util.concurrent.TimeUnit

/**
 * Resilience backstop. The foreground service handles the 1-minute cadence; this
 * periodic worker flushes any backlog if the service was killed or never started.
 * WorkManager's minimum period is 15 minutes.
 */
class SyncWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result =
        when (applicationContext.graph.repository.syncOnce()) {
            is SyncResult.Error -> Result.retry()
            else -> Result.success()
        }

    companion object {
        private const val UNIQUE_NAME = "guardian-vitals-sync"

        fun enqueuePeriodic(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()
            val request = PeriodicWorkRequestBuilder<SyncWorker>(15, TimeUnit.MINUTES)
                .setConstraints(constraints)
                .build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                UNIQUE_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                request,
            )
        }
    }
}
