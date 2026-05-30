package com.guardian.watch

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.lifecycle.viewmodel.compose.viewModel
import com.guardian.watch.ui.MainScreen
import com.guardian.watch.ui.MonitorViewModel
import com.guardian.watch.ui.SettingsScreen
import com.guardian.watch.ui.theme.GuardianWatchTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            GuardianWatchTheme { GuardianApp() }
        }
    }
}

private enum class Screen { Monitor, Settings }

@Composable
private fun GuardianApp(vm: MonitorViewModel = viewModel()) {
    val state by vm.uiState.collectAsState()
    var screen by remember { mutableStateOf(Screen.Monitor) }

    // Ask for the sensor + notification permissions on first launch.
    val permissions = remember { requiredPermissions() }
    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { /* UI reflects whatever the user grants */ }
    LaunchedEffect(Unit) {
        if (permissions.isNotEmpty()) launcher.launch(permissions)
    }

    when (screen) {
        Screen.Monitor -> MainScreen(
            state = state,
            onToggleMonitoring = { on -> if (on) vm.startMonitoring() else vm.stopMonitoring() },
            onSyncNow = vm::syncNow,
            onOpenSettings = { screen = Screen.Settings },
        )

        Screen.Settings -> SettingsScreen(
            initialBaseUrl = state.baseUrl,
            initialPatientId = state.patientId,
            onSave = vm::saveSettings,
            onBack = { screen = Screen.Monitor },
        )
    }
}

private fun requiredPermissions(): Array<String> = buildList {
    add(Manifest.permission.BODY_SENSORS)
    add(Manifest.permission.ACTIVITY_RECOGNITION)
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        add(Manifest.permission.POST_NOTIFICATIONS)
    }
}.toTypedArray()
