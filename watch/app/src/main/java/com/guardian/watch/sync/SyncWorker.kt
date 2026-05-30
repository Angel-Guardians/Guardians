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
import com.guardian.watch.di.GuardianGraph
import com.guardian.watch.graph
import kotlinx.coroutines.flow.first
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

    override suspend fun doWork(): Result {
        val graph = applicationContext.graph
        // Best-effort supplement: pull anything the device's health app recorded
        // since we last looked. Never let a Health Connect hiccup fail the sync.
        runCatching { pullHealthConnect(graph) }
        return when (graph.repository.syncOnce()) {
            is SyncResult.Error -> Result.retry()
            else -> Result.success()
        }
    }

    /** Read new Health Connect records into Room, advancing the watermark on success. */
    private suspend fun pullHealthConnect(graph: GuardianGraph) {
        val hc = graph.healthConnectManager
        if (!hc.isAvailable() || !hc.hasAllPermissions()) return

        val now = System.currentTimeMillis()
        val watermark = graph.settings.healthConnectSyncedThrough.first()
        // First run: bound the initial look-back so we don't ingest a huge history.
        val start = if (watermark <= 0L) now - INITIAL_LOOKBACK_MS else watermark
        if (start >= now) return

        graph.repository.recordAll(hc.readNewReadings(start, now))
        graph.settings.setHealthConnectSyncedThrough(now)
    }

    companion object {
        private const val UNIQUE_NAME = "guardian-vitals-sync"
        private const val INITIAL_LOOKBACK_MS = 7L * 24 * 60 * 60 * 1000

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
