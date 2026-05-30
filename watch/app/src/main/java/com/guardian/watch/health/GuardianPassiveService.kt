package com.guardian.watch.health

import androidx.health.services.client.PassiveListenerService
import androidx.health.services.client.data.DataPointContainer
import androidx.health.services.client.data.DataType
import com.guardian.watch.data.local.VitalReading
import com.guardian.watch.graph
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/**
 * Receives passive (background) data points from Health Services and persists
 * them. The system binds and delivers to this service even when the app's UI
 * isn't running, which is what makes offline recording possible.
 */
class GuardianPassiveService : PassiveListenerService() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onNewDataPointsReceived(dataPoints: DataPointContainer) {
        val now = System.currentTimeMillis()
        val readings = buildList {
            for (p in dataPoints.getData(DataType.STEPS_DAILY)) {
                add(VitalReading(kind = "steps", value = p.value.toDouble(), ts = now))
            }
            for (p in dataPoints.getData(DataType.CALORIES_DAILY)) {
                add(VitalReading(kind = "calories", value = p.value, ts = now))
            }
        }
        if (readings.isEmpty()) return
        val repository = applicationContext.graph.repository
        scope.launch { repository.recordAll(readings) }
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }
}
