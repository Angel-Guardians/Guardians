package com.guardian.watch.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.wear.compose.foundation.lazy.ScalingLazyColumn
import androidx.wear.compose.foundation.lazy.rememberScalingLazyListState
import androidx.wear.compose.material.Chip
import androidx.wear.compose.material.ChipDefaults
import androidx.wear.compose.material.CompactChip
import androidx.wear.compose.material.Icon
import androidx.wear.compose.material.MaterialTheme
import androidx.wear.compose.material.PositionIndicator
import androidx.wear.compose.material.Scaffold
import androidx.wear.compose.material.Stepper
import androidx.wear.compose.material.StepperDefaults
import androidx.wear.compose.material.Text
import androidx.wear.compose.material.TimeText

@Composable
fun SettingsScreen(
    initialBaseUrl: String,
    initialPatientId: Int,
    onSave: (String, Int) -> Unit,
    onBack: () -> Unit,
) {
    var baseUrl by remember(initialBaseUrl) { mutableStateOf(initialBaseUrl) }
    var patientId by remember(initialPatientId) { mutableIntStateOf(initialPatientId) }
    val listState = rememberScalingLazyListState()

    Scaffold(
        timeText = { TimeText() },
        positionIndicator = { PositionIndicator(scalingLazyListState = listState) },
    ) {
        ScalingLazyColumn(
            state = listState,
            modifier = Modifier.fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            item { Text("Settings", style = MaterialTheme.typography.title3) }

            item {
                Text(
                    "Backend URL",
                    style = MaterialTheme.typography.caption1,
                    color = MaterialTheme.colors.onSurfaceVariant,
                )
            }
            item { UrlField(value = baseUrl, onValueChange = { baseUrl = it }) }

            item {
                Text(
                    "Patient ID",
                    style = MaterialTheme.typography.caption1,
                    color = MaterialTheme.colors.onSurfaceVariant,
                )
            }
            item {
                Stepper(
                    value = patientId,
                    onValueChange = { patientId = it },
                    valueProgression = 1..50,
                    increaseIcon = { Icon(StepperDefaults.Increase, contentDescription = "Increase") },
                    decreaseIcon = { Icon(StepperDefaults.Decrease, contentDescription = "Decrease") },
                ) {
                    Text("Patient $patientId", style = MaterialTheme.typography.title3)
                }
            }

            item {
                Chip(
                    onClick = {
                        onSave(baseUrl.trim(), patientId)
                        onBack()
                    },
                    label = { Text("Save") },
                    colors = ChipDefaults.primaryChipColors(),
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            item { CompactChip(onClick = onBack, label = { Text("Cancel") }) }
        }
    }
}

@Composable
private fun UrlField(value: String, onValueChange: (String) -> Unit) {
    BasicTextField(
        value = value,
        onValueChange = onValueChange,
        singleLine = true,
        textStyle = MaterialTheme.typography.body2.copy(
            color = MaterialTheme.colors.onSurface,
            textAlign = TextAlign.Center,
        ),
        cursorBrush = SolidColor(MaterialTheme.colors.primary),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
        modifier = Modifier
            .fillMaxWidth()
            .background(MaterialTheme.colors.surface, RoundedCornerShape(14.dp))
            .padding(horizontal = 12.dp, vertical = 10.dp),
        decorationBox = { inner ->
            Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                if (value.isEmpty()) {
                    Text(
                        "http://192.168.1.50:8000",
                        style = MaterialTheme.typography.body2,
                        color = MaterialTheme.colors.onSurfaceVariant,
                    )
                }
                inner()
            }
        },
    )
}
