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
