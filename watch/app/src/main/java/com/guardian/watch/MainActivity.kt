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
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.health.connect.client.PermissionController
import androidx.lifecycle.viewmodel.compose.viewModel
import com.guardian.watch.ui.MainScreen
import com.guardian.watch.ui.MonitorViewModel
import com.guardian.watch.ui.SettingsScreen
import com.guardian.watch.ui.theme.GuardianWatchTheme
import kotlinx.coroutines.launch

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
    val voice by vm.voiceState.collectAsState()
    var screen by remember { mutableStateOf(Screen.Monitor) }

    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    // Health Connect is optional (Wear OS 5+). Its reads use a separate permission
    // flow; request them once the standard sensor permissions are dealt with.
    val healthConnect = remember { context.graph.healthConnectManager }
    val healthConnectLauncher = rememberLauncherForActivityResult(
        PermissionController.createRequestPermissionResultContract(),
    ) { /* grants are re-checked at read time in SyncWorker */ }

    // Ask for the sensor + notification permissions on first launch.
    val permissions = remember { requiredPermissions() }
    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) {
        if (healthConnect.isAvailable()) scope.launch {
            if (!healthConnect.hasAllPermissions()) {
                healthConnectLauncher.launch(healthConnect.permissions)
            }
        }
    }
    LaunchedEffect(Unit) {
        vm.resumeMonitoringIfActive()
        if (permissions.isNotEmpty()) launcher.launch(permissions)
    }

    when (screen) {
        Screen.Monitor -> MainScreen(
            state = state,
            voice = voice,
            onTalkStart = vm::startTalking,
            onTalkStop = vm::stopTalking,
            onToggleMonitoring = { on -> if (on) vm.startMonitoring() else vm.stopMonitoring() },
            onSyncNow = vm::syncNow,
            onTestFall = vm::simulateFall,
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
    add(Manifest.permission.RECORD_AUDIO)
    add(Manifest.permission.ACCESS_FINE_LOCATION)
    add(Manifest.permission.ACCESS_COARSE_LOCATION)
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        add(Manifest.permission.POST_NOTIFICATIONS)
    }
}.toTypedArray()
