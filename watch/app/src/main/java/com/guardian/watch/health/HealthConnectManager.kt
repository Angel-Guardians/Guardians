package com.guardian.watch.health

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.HeartRateVariabilityRmssdRecord
import androidx.health.connect.client.records.OxygenSaturationRecord
import androidx.health.connect.client.records.Record
import androidx.health.connect.client.records.RestingHeartRateRecord
import androidx.health.connect.client.records.SleepSessionRecord
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import com.guardian.watch.data.local.VitalReading
import java.time.Duration
import java.time.Instant
import kotlin.reflect.KClass

/**
 * Optional supplement to [HealthServicesManager]. Where a Health Connect provider
 * exists (Wear OS 5+, modern phones), this reads metrics the device's own health
 * app has already recorded — SpO2, resting heart rate, HRV, sleep — that the live
 * Health Services path doesn't measure. The watch app stays the *consumer* here;
 * something else (Samsung Health, Fitbit, Google Fit, …) is what populates the store.
 *
 * Everything is guarded so the whole feature is a clean no-op on watches without
 * Health Connect (Galaxy Watch 4/5 on Wear OS 3/4): [isAvailable] is false there,
 * the client is never created, and [readNewReadings] returns empty.
 */
class HealthConnectManager(private val context: Context) {

    /** The read permissions Health Connect must grant before any record is returned. */
    val permissions: Set<String> = setOf(
        HealthPermission.getReadPermission(OxygenSaturationRecord::class),
        HealthPermission.getReadPermission(RestingHeartRateRecord::class),
        HealthPermission.getReadPermission(HeartRateVariabilityRmssdRecord::class),
        HealthPermission.getReadPermission(SleepSessionRecord::class),
    )

    /** True only where a current Health Connect provider is installed. */
    fun isAvailable(): Boolean =
        HealthConnectClient.getSdkStatus(context) == HealthConnectClient.SDK_AVAILABLE

    // Created lazily and only when available — getOrCreate throws otherwise.
    private val client: HealthConnectClient? by lazy {
        if (isAvailable()) HealthConnectClient.getOrCreate(context) else null
    }

    suspend fun hasAllPermissions(): Boolean {
        val c = client ?: return false
        return c.permissionController.getGrantedPermissions().containsAll(permissions)
    }

    /**
     * Read records stored between [startMillis] and [endMillis], mapped to the
     * app's [VitalReading] vocabulary ("spo2", "resting_hr", "hrv",
     * "sleep_minutes" — all free-form on the backend). Returns empty if Health
     * Connect is absent or the read permissions aren't all granted, so callers
     * never special-case the unsupported path.
     */
    suspend fun readNewReadings(startMillis: Long, endMillis: Long): List<VitalReading> {
        val c = client ?: return emptyList()
        if (!c.permissionController.getGrantedPermissions().containsAll(permissions)) return emptyList()

        val range = TimeRangeFilter.between(
            Instant.ofEpochMilli(startMillis),
            Instant.ofEpochMilli(endMillis),
        )
        return buildList {
            c.readSafely(OxygenSaturationRecord::class, range).forEach {
                add(VitalReading(kind = "spo2", value = it.percentage.value, ts = it.time.toEpochMilli()))
            }
            c.readSafely(RestingHeartRateRecord::class, range).forEach {
                add(VitalReading(kind = "resting_hr", value = it.beatsPerMinute.toDouble(), ts = it.time.toEpochMilli()))
            }
            c.readSafely(HeartRateVariabilityRmssdRecord::class, range).forEach {
                add(VitalReading(kind = "hrv", value = it.heartRateVariabilityMillis, ts = it.time.toEpochMilli()))
            }
            c.readSafely(SleepSessionRecord::class, range).forEach {
                val minutes = Duration.between(it.startTime, it.endTime).toMinutes().toDouble()
                add(VitalReading(kind = "sleep_minutes", value = minutes, ts = it.endTime.toEpochMilli()))
            }
        }
    }

    /** One record type's reads, isolated so a single failing type can't sink the batch. */
    private suspend fun <T : Record> HealthConnectClient.readSafely(
        type: KClass<T>,
        range: TimeRangeFilter,
    ): List<T> =
        runCatching { readRecords(ReadRecordsRequest(type, range)).records }.getOrDefault(emptyList())
}
