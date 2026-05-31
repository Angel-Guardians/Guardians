package com.guardian.watch.ui

import android.text.format.DateUtils
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.wear.compose.foundation.lazy.ScalingLazyColumn
import androidx.wear.compose.foundation.lazy.rememberScalingLazyListState
import androidx.wear.compose.material.Chip
import androidx.wear.compose.material.ChipDefaults
import androidx.wear.compose.material.Icon
import androidx.wear.compose.material.MaterialTheme
import androidx.wear.compose.material.PositionIndicator
import androidx.wear.compose.material.Scaffold
import androidx.wear.compose.material.Text
import androidx.wear.compose.material.TimeText
import androidx.wear.compose.material.ToggleChip
import androidx.wear.compose.material.ToggleChipDefaults
import androidx.wear.compose.material.Vignette
import androidx.wear.compose.material.VignettePosition
import kotlin.math.roundToInt

@Composable
fun MainScreen(
    state: MonitorUiState,
    onToggleMonitoring: (Boolean) -> Unit,
    onSyncNow: () -> Unit,
    onTestFall: () -> Unit,
    onOpenSettings: () -> Unit,
) {
    val listState = rememberScalingLazyListState()
    Scaffold(
        timeText = { TimeText() },
        vignette = { Vignette(vignettePosition = VignettePosition.TopAndBottom) },
        positionIndicator = { PositionIndicator(scalingLazyListState = listState) },
    ) {
        ScalingLazyColumn(
            state = listState,
            modifier = Modifier.fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            item { Text(text = "Guardian", style = MaterialTheme.typography.title3) }

            item {
                Metric(
                    value = state.heartRate?.let { "${it.roundToInt()}" } ?: "--",
                    label = "bpm",
                )
            }

            item {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp),
                    horizontalArrangement = Arrangement.SpaceEvenly,
                ) {
                    Metric(state.steps?.let { it.roundToInt().toString() } ?: "--", "steps")
                    Metric(state.calories?.let { it.roundToInt().toString() } ?: "--", "kcal")
                }
            }

            if (state.spo2 != null || state.restingHr != null ||
                state.hrv != null || state.sleepMinutes != null
            ) {
                item {
                    Text(
                        "Health app",
                        style = MaterialTheme.typography.caption1,
                        color = MaterialTheme.colors.onSurfaceVariant,
                    )
                }
                item {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp),
                        horizontalArrangement = Arrangement.SpaceEvenly,
                    ) {
                        Metric(state.spo2?.let { "${it.roundToInt()}%" } ?: "--", "SpO2")
                        Metric(state.restingHr?.let { it.roundToInt().toString() } ?: "--", "rest bpm")
                    }
                }
                item {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp),
                        horizontalArrangement = Arrangement.SpaceEvenly,
                    ) {
                        Metric(state.hrv?.let { it.roundToInt().toString() } ?: "--", "HRV ms")
                        Metric(state.sleepMinutes?.let { formatSleep(it) } ?: "--", "sleep")
                    }
                }
            }

            item {
                ToggleChip(
                    checked = state.monitoring,
                    onCheckedChange = onToggleMonitoring,
                    label = { Text("Monitoring") },
                    toggleControl = {
                        Icon(
                            imageVector = ToggleChipDefaults.switchIcon(state.monitoring),
                            contentDescription = if (state.monitoring) "On" else "Off",
                        )
                    },
                    modifier = Modifier.fillMaxWidth(),
                )
            }

            item {
                Text(
                    "Safety",
                    style = MaterialTheme.typography.caption1,
                    color = MaterialTheme.colors.onSurfaceVariant,
                )
            }
            item { FallStatus(kind = state.fallKind, at = state.fallAt) }
            item {
                Chip(
                    onClick = onTestFall,
                    label = { Text("Test fall alert") },
                    secondaryLabel = { Text("send a fall to the server") },
                    colors = ChipDefaults.secondaryChipColors(),
                    modifier = Modifier.fillMaxWidth(),
                )
            }

            item {
                Chip(
                    onClick = onSyncNow,
                    label = { Text("Sync now") },
                    secondaryLabel = { Text(syncSubtitle(state)) },
                    colors = ChipDefaults.secondaryChipColors(),
                    modifier = Modifier.fillMaxWidth(),
                )
            }

            item {
                Chip(
                    onClick = onOpenSettings,
                    label = { Text("Settings") },
                    secondaryLabel = {
                        Text(if (state.baseUrl.isBlank()) "Set backend URL" else state.baseUrl)
                    },
                    colors = ChipDefaults.secondaryChipColors(),
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
}

@Composable
private fun Metric(value: String, label: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, style = MaterialTheme.typography.display3)
        Text(
            label,
            style = MaterialTheme.typography.caption2,
            color = MaterialTheme.colors.onSurfaceVariant,
        )
    }
}

@Composable
private fun FallStatus(kind: String?, at: Long) {
    val (label, color) = when (kind) {
        "fall_confirmed" -> "Fall confirmed" to MaterialTheme.colors.error
        "fall_suspected" -> "Fall suspected" to MaterialTheme.colors.error
        "fall_cancelled" -> "Marked OK" to MaterialTheme.colors.primary
        else -> "No falls detected" to MaterialTheme.colors.onSurfaceVariant
    }
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(label, style = MaterialTheme.typography.title3, color = color)
        if (kind != null && at > 0L) {
            Text(
                DateUtils.getRelativeTimeSpanString(
                    at, System.currentTimeMillis(), DateUtils.MINUTE_IN_MILLIS,
                ).toString(),
                style = MaterialTheme.typography.caption2,
                color = MaterialTheme.colors.onSurfaceVariant,
            )
        }
    }
}

private fun formatSleep(minutes: Double): String = "%.1fh".format(minutes / 60.0)

private fun syncSubtitle(state: MonitorUiState): String {
    val pending = if (state.unsent > 0) "${state.unsent} pending" else "Up to date"
    if (state.lastSyncAt <= 0L) return pending
    val ago = DateUtils.getRelativeTimeSpanString(
        state.lastSyncAt,
        System.currentTimeMillis(),
        DateUtils.MINUTE_IN_MILLIS,
    )
    return "$pending · $ago"
}
