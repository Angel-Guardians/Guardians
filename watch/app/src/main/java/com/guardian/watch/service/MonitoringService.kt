package com.guardian.watch.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import com.guardian.watch.MainActivity
import com.guardian.watch.R
import com.guardian.watch.graph
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * Foreground service that does the real work while monitoring is on:
 *   1. streams live heart rate into Room,
 *   2. keeps steps/calories flowing via passive monitoring,
 *   3. uploads unsent readings to the backend once a minute.
 *
 * The 1-minute cadence lives here (not in WorkManager) because WorkManager's
 * minimum periodic interval is 15 minutes.
 */
class MonitoringService : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        // Starting a "health" foreground service requires a granted health
        // permission (e.g. BODY_SENSORS). If that's missing, bail cleanly rather
        // than crash — the UI requests permissions before monitoring is started.
        try {
            startForegroundNotification()
        } catch (e: Exception) {
            stopSelf()
            return
        }

        val g = applicationContext.graph
        scope.launch { g.settings.setMonitoringActive(true) }

        // Steps / calories in the background.
        scope.launch { runCatching { g.healthServicesManager.registerPassive() } }

        // Live heart rate -> Room.
        g.healthServicesManager.heartRateFlow()
            .onEach { bpm -> g.repository.record(kind = "hr", value = bpm) }
            .catch { /* sensor unavailable or permission revoked; keep service alive */ }
            .launchIn(scope)

        // Offline-first upload loop.
        scope.launch {
            while (isActive) {
                runCatching { g.repository.syncOnce() }
                delay(SYNC_INTERVAL_MS)
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY

    override fun onDestroy() {
        // Detached scope so cleanup completes even as the service scope cancels.
        val g = applicationContext.graph
        CoroutineScope(Dispatchers.IO + SupervisorJob()).launch {
            g.settings.setMonitoringActive(false)
            runCatching { g.healthServicesManager.unregisterPassive() }
        }
        scope.cancel()
        super.onDestroy()
    }

    private fun startForegroundNotification() {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                getString(R.string.monitoring_channel_name),
                NotificationManager.IMPORTANCE_LOW,
            ).apply { description = getString(R.string.monitoring_channel_desc) }
            nm.createNotificationChannel(channel)
        }

        val contentIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE,
        )

        val notification: Notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.monitoring_notification_title))
            .setContentText(getString(R.string.monitoring_notification_text))
            .setSmallIcon(R.drawable.ic_heart)
            .setOngoing(true)
            .setContentIntent(contentIntent)
            .build()

        val type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            ServiceInfo.FOREGROUND_SERVICE_TYPE_HEALTH
        } else {
            0
        }
        ServiceCompat.startForeground(this, NOTIFICATION_ID, notification, type)
    }

    companion object {
        private const val CHANNEL_ID = "guardian_monitoring"
        private const val NOTIFICATION_ID = 1001
        private const val SYNC_INTERVAL_MS = 60_000L

        fun start(context: Context) {
            ContextCompat.startForegroundService(
                context,
                Intent(context, MonitoringService::class.java),
            )
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, MonitoringService::class.java))
        }
    }
}
