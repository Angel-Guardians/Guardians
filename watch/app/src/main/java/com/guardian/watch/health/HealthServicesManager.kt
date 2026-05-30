package com.guardian.watch.health

import android.content.Context
import androidx.health.services.client.HealthServices
import androidx.health.services.client.MeasureCallback
import androidx.health.services.client.data.Availability
import androidx.health.services.client.data.DataPointContainer
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.DeltaDataType
import androidx.health.services.client.data.PassiveListenerConfig
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.guava.await

/**
 * Thin wrapper over Wear OS Health Services.
 *
 *  - Heart rate: [heartRateFlow] streams live samples via [MeasureClient] while
 *    a foreground service is collecting it.
 *  - Steps / calories: [registerPassive] hands those daily totals to
 *    [GuardianPassiveService] for low-power background delivery.
 */
class HealthServicesManager(context: Context) {

    private val client = HealthServices.getClient(context)
    private val measureClient = client.measureClient
    private val passiveClient = client.passiveMonitoringClient

    suspend fun supportsHeartRate(): Boolean {
        val caps = measureClient.getCapabilitiesAsync().await()
        return DataType.HEART_RATE_BPM in caps.supportedDataTypesMeasure
    }

    /** Live heart-rate samples in bpm; emits only while collected. */
    fun heartRateFlow(): Flow<Double> = callbackFlow {
        val callback = object : MeasureCallback {
            override fun onAvailabilityChanged(
                dataType: DeltaDataType<*, *>,
                availability: Availability,
            ) {
                // Availability transitions (e.g. watch not on wrist) could be
                // surfaced to the UI here if needed.
            }

            override fun onDataReceived(data: DataPointContainer) {
                for (point in data.getData(DataType.HEART_RATE_BPM)) {
                    trySend(point.value)
                }
            }
        }
        measureClient.registerMeasureCallback(DataType.HEART_RATE_BPM, callback)
        awaitClose {
            measureClient.unregisterMeasureCallbackAsync(DataType.HEART_RATE_BPM, callback)
        }
    }

    /** Subscribe [GuardianPassiveService] to daily steps + calories, if supported. */
    suspend fun registerPassive() {
        val caps = passiveClient.getCapabilitiesAsync().await()
        val requested: Set<DataType<*, *>> = setOf(DataType.STEPS_DAILY, DataType.CALORIES_DAILY)
        val supported = requested.filter { it in caps.supportedDataTypesPassiveMonitoring }.toSet()
        if (supported.isEmpty()) return
        val config = PassiveListenerConfig.builder().setDataTypes(supported).build()
        passiveClient
            .setPassiveListenerServiceAsync(GuardianPassiveService::class.java, config)
            .await()
    }

    suspend fun unregisterPassive() {
        passiveClient.clearPassiveListenerServiceAsync().await()
    }
}
