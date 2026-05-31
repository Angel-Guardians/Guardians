package com.guardian.watch.location

import android.annotation.SuppressLint
import android.content.Context
import android.location.Location
import android.location.LocationManager
import android.os.Build
import android.os.CancellationSignal
import androidx.core.content.getSystemService
import kotlinx.coroutines.suspendCancellableCoroutine
import java.util.concurrent.Executors
import kotlin.coroutines.resume

/**
 * Single-shot location fetch via the framework [LocationManager] — deliberately
 * no Play Services dependency.
 *
 * Prefers the **FUSED** provider, which yields a position indoors via Wi-Fi /
 * network (GPS alone never locks without sky view), then NETWORK, then GPS. If
 * no fresh fix is available it falls back to the newest cached fix so a
 * momentary miss still produces a point. The monitoring service holds the
 * location permission; we catch [SecurityException] defensively and return null.
 */
class LocationProvider(context: Context) {

    private val appContext = context.applicationContext
    private val locationManager = appContext.getSystemService<LocationManager>()
    private val executor = Executors.newSingleThreadExecutor()

    suspend fun current(): Location? {
        val lm = locationManager ?: return null
        bestProvider(lm)?.let { provider ->
            fetchCurrent(lm, provider)?.let { return it }
        }
        // No fresh fix (e.g. indoors with no GPS lock) — use the newest cache.
        return lastKnown(lm)
    }

    @SuppressLint("MissingPermission")
    private suspend fun fetchCurrent(lm: LocationManager, provider: String): Location? = try {
        suspendCancellableCoroutine { cont ->
            val signal = CancellationSignal()
            cont.invokeOnCancellation { signal.cancel() }
            lm.getCurrentLocation(provider, signal, executor) { location ->
                cont.resume(location)
            }
        }
    } catch (e: Exception) {
        null
    }

    @SuppressLint("MissingPermission")
    private fun lastKnown(lm: LocationManager): Location? =
        providers()
            .mapNotNull { p -> runCatching { lm.getLastKnownLocation(p) }.getOrNull() }
            .maxByOrNull { it.time }

    private fun bestProvider(lm: LocationManager): String? =
        providers().firstOrNull { runCatching { lm.isProviderEnabled(it) }.getOrDefault(false) }

    private fun providers(): List<String> = buildList {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) add(LocationManager.FUSED_PROVIDER)
        add(LocationManager.NETWORK_PROVIDER)
        add(LocationManager.GPS_PROVIDER)
    }
}
