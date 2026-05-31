package com.guardian.watch.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.guardian.watch.graph
import com.guardian.watch.service.MonitoringService
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class MonitorUiState(
    val monitoring: Boolean = false,
    val heartRate: Double? = null,
    val steps: Double? = null,
    val calories: Double? = null,
    val spo2: Double? = null,
    val restingHr: Double? = null,
    val hrv: Double? = null,
    val sleepMinutes: Double? = null,
    val unsent: Int = 0,
    val lastSyncAt: Long = 0L,
    val lastSyncStatus: String = "",
    val baseUrl: String = "",
    val patientId: Int = 1,
    val fallKind: String? = null,
    val fallAt: Long = 0L,
)

class MonitorViewModel(app: Application) : AndroidViewModel(app) {

    private val graph = app.graph
    private val repo = graph.repository
    private val settings = graph.settings
    private val voice = graph.voiceSession

    /** Push-to-talk voice state (transcript, reply, current phase). */
    val voiceState = voice.state

    private val vitals = combine(
        repo.latest("hr"),
        repo.latest("steps"),
        repo.latest("calories"),
        repo.unsentCount(),
    ) { hr, steps, calories, unsent ->
        Vitals(hr?.value, steps?.value, calories?.value, unsent)
    }

    // Supplemental metrics pulled from Health Connect (null until/unless present).
    private val healthConnect = combine(
        repo.latest("spo2"),
        repo.latest("resting_hr"),
        repo.latest("hrv"),
        repo.latest("sleep_minutes"),
    ) { spo2, restingHr, hrv, sleep ->
        HcVitals(spo2?.value, restingHr?.value, hrv?.value, sleep?.value)
    }

    private val config = combine(
        settings.monitoringActive,
        settings.baseUrl,
        settings.patientId,
    ) { monitoring, baseUrl, patientId -> Config(monitoring, baseUrl, patientId) }

    private val sync = combine(
        settings.lastSyncAt,
        settings.lastSyncStatus,
    ) { at, status -> Sync(at, status) }

    val uiState: StateFlow<MonitorUiState> =
        combine(vitals, healthConnect, config, sync, repo.latestFall()) { v, h, c, s, fall ->
            MonitorUiState(
                monitoring = c.monitoring,
                heartRate = v.hr,
                steps = v.steps,
                calories = v.calories,
                spo2 = h.spo2,
                restingHr = h.restingHr,
                hrv = h.hrv,
                sleepMinutes = h.sleepMinutes,
                unsent = v.unsent,
                lastSyncAt = s.at,
                lastSyncStatus = s.status,
                baseUrl = c.baseUrl,
                patientId = c.patientId,
                fallKind = fall?.kind,
                fallAt = fall?.ts ?: 0L,
            )
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), MonitorUiState())

    fun startMonitoring() = MonitoringService.start(getApplication())

    fun stopMonitoring() = MonitoringService.stop(getApplication())

    /**
     * Self-heal: if the saved state says monitoring is on but the service isn't
     * actually running (after a reinstall / reboot), bring it back. Safe to call
     * on every launch — start() is idempotent.
     */
    fun resumeMonitoringIfActive() {
        viewModelScope.launch {
            if (settings.monitoringActive.first()) startMonitoring()
        }
    }

    fun syncNow() {
        viewModelScope.launch { repo.syncOnce() }
    }

    fun saveSettings(baseUrl: String, patientId: Int) {
        viewModelScope.launch {
            settings.setBaseUrl(baseUrl)
            settings.setPatientId(patientId)
        }
    }

    /** Hands-free voice: when on, the watch listens and streams when speech is detected. */
    fun setVoiceEnabled(on: Boolean) = voice.setEnabled(on)

    override fun onCleared() {
        voice.shutdown()
        super.onCleared()
    }

    /** Demo/QA: fire a fall straight at the server to test the alert pipeline. */
    fun simulateFall() {
        viewModelScope.launch {
            // Routed through the real "fall_suspected" path; 3.5 g ≈ a plausible impact.
            repo.record(kind = "fall_suspected", value = 3.5)
            runCatching { repo.syncOnce() }
        }
    }

    private data class Vitals(val hr: Double?, val steps: Double?, val calories: Double?, val unsent: Int)
    private data class HcVitals(val spo2: Double?, val restingHr: Double?, val hrv: Double?, val sleepMinutes: Double?)
    private data class Config(val monitoring: Boolean, val baseUrl: String, val patientId: Int)
    private data class Sync(val at: Long, val status: String)
}
