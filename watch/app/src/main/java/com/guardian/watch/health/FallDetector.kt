package com.guardian.watch.health

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import kotlin.math.sqrt

/**
 * Threshold-based fall detector driven by the accelerometer.
 *
 * Classic three-phase heuristic:
 *   1. **free-fall** — acceleration magnitude dips toward 0 g as the body drops,
 *   2. **impact**    — a sharp spike when it hits the ground,
 *   3. **stillness** — the person lies relatively motionless afterwards.
 *
 * Requiring a free-fall *before* the impact filters out most everyday spikes
 * (clapping, setting the watch down, a hard hand-tap). It is **demo-grade, not
 * medical-grade** — tune the constants below for your wrist and surfaces.
 *
 * No runtime permission is needed for the accelerometer at this sampling rate.
 */
class FallDetector(
    context: Context,
    private val onFall: (peakG: Float) -> Unit,
) : SensorEventListener {

    private val sensorManager =
        context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val accelerometer: Sensor? =
        sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)

    private enum class Phase { IDLE, FREE_FALL, POST_IMPACT }

    private var phase = Phase.IDLE
    private var freeFallAtMs = 0L
    private var impactAtMs = 0L
    private var peakImpact = 0f
    private var stillnessBroken = false
    private var lastFallFiredMs = 0L

    /** True only if the device actually has an accelerometer. */
    val isSupported: Boolean get() = accelerometer != null

    fun start() {
        val sensor = accelerometer ?: return
        sensorManager.registerListener(this, sensor, SAMPLING_US)
    }

    fun stop() {
        sensorManager.unregisterListener(this)
        phase = Phase.IDLE
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit

    override fun onSensorChanged(event: SensorEvent) {
        val gMag = sqrt(
            event.values[0] * event.values[0] +
                event.values[1] * event.values[1] +
                event.values[2] * event.values[2],
        ) / GRAVITY // normalize: 1.0 ≈ at rest, 0 ≈ free fall

        val now = System.currentTimeMillis()

        when (phase) {
            Phase.IDLE ->
                if (gMag < FREE_FALL_G) {
                    phase = Phase.FREE_FALL
                    freeFallAtMs = now
                }

            Phase.FREE_FALL ->
                if (gMag > IMPACT_G) {
                    phase = Phase.POST_IMPACT
                    impactAtMs = now
                    peakImpact = gMag
                    stillnessBroken = false
                } else if (now - freeFallAtMs > FREE_FALL_MAX_MS) {
                    phase = Phase.IDLE // free-fall fizzled without an impact
                }

            Phase.POST_IMPACT -> {
                peakImpact = maxOf(peakImpact, gMag)
                val sinceImpact = now - impactAtMs
                // Ignore the brief settling right after impact, then any vigorous
                // motion means the person is moving — not lying fallen.
                if (sinceImpact > SETTLE_MS && (gMag > MOVING_HIGH_G || gMag < MOVING_LOW_G)) {
                    stillnessBroken = true
                }
                if (sinceImpact >= STILLNESS_WINDOW_MS) {
                    if (!stillnessBroken && now - lastFallFiredMs > COOLDOWN_MS) {
                        lastFallFiredMs = now
                        onFall(peakImpact)
                    }
                    phase = Phase.IDLE
                }
            }
        }
    }

    companion object {
        private val GRAVITY = SensorManager.GRAVITY_EARTH // 9.80665 m/s²
        private val SAMPLING_US = SensorManager.SENSOR_DELAY_GAME // ~50 Hz

        // --- tunables, in g ---
        // Tuned MORE sensitive: an easier free-fall entry, a lower impact spike,
        // and a wider "still" band so a real fall is caught more readily.
        private const val FREE_FALL_G = 0.72f   // magnitude dips below this while falling
        private const val IMPACT_G = 1.7f       // landing spike
        private const val MOVING_LOW_G = 0.4f   // "still" band, lower bound
        private const val MOVING_HIGH_G = 1.9f  // "still" band, upper bound

        // --- tunables, in ms ---
        private const val FREE_FALL_MAX_MS = 1500L   // impact must follow free-fall within this
        private const val SETTLE_MS = 400L           // grace period after impact (bounce/settle)
        private const val STILLNESS_WINDOW_MS = 1500L
        private const val COOLDOWN_MS = 30_000L      // debounce repeated alerts
    }
}
