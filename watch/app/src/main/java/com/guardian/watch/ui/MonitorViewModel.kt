package com.guardian.watch.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.guardian.watch.graph
import com.guardian.watch.service.MonitoringService
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class MonitorUiState(
    val monitoring: Boolean = false,
    val heartRate: Double? = null,
    val steps: Double? = null,
    val calories: Double? = null,
    val unsent: Int = 0,
    val lastSyncAt: Long = 0L,
    val lastSyncStatus: String = "",
    val baseUrl: String = "",
    val patientId: Int = 1,
)

class MonitorViewModel(app: Application) : AndroidViewModel(app) {

    private val graph = app.graph
    private val repo = graph.repository
    private val settings = graph.settings

    private val vitals = combine(
        repo.latest("hr"),
        repo.latest("steps"),
        repo.latest("calories"),
        repo.unsentCount(),
    ) { hr, steps, calories, unsent ->
        Vitals(hr?.value, steps?.value, calories?.value, unsent)
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
        combine(vitals, config, sync) { v, c, s ->
            MonitorUiState(
                monitoring = c.monitoring,
                heartRate = v.hr,
                steps = v.steps,
                calories = v.calories,
                unsent = v.unsent,
                lastSyncAt = s.at,
                lastSyncStatus = s.status,
                baseUrl = c.baseUrl,
                patientId = c.patientId,
            )
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), MonitorUiState())

    fun startMonitoring() = MonitoringService.start(getApplication())

    fun stopMonitoring() = MonitoringService.stop(getApplication())

    fun syncNow() {
        viewModelScope.launch { repo.syncOnce() }
    }

    fun saveSettings(baseUrl: String, patientId: Int) {
        viewModelScope.launch {
            settings.setBaseUrl(baseUrl)
            settings.setPatientId(patientId)
        }
    }

    private data class Vitals(val hr: Double?, val steps: Double?, val calories: Double?, val unsent: Int)
    private data class Config(val monitoring: Boolean, val baseUrl: String, val patientId: Int)
    private data class Sync(val at: Long, val status: String)
}
