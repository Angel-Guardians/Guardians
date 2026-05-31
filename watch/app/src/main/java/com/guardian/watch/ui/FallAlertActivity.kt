package com.guardian.watch.ui

import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.wear.compose.material.Chip
import androidx.wear.compose.material.ChipDefaults
import androidx.wear.compose.material.CompactChip
import androidx.wear.compose.material.MaterialTheme
import androidx.wear.compose.material.Text
import com.guardian.watch.graph
import com.guardian.watch.ui.theme.GuardianWatchTheme
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

private const val COUNTDOWN_SEC = 30

/**
 * Full-screen "Are you OK?" prompt shown when a fall is suspected. If the wearer
 * doesn't respond within [COUNTDOWN_SEC] seconds we treat it as a confirmed fall.
 *
 * Outcomes are recorded as readings and flushed to the backend immediately:
 *   - "I'm OK" / swipe-back  -> `fall_cancelled`
 *   - countdown expires      -> `fall_confirmed`
 */
class FallAlertActivity : ComponentActivity() {

    private var peakG = 0f

    @Suppress("DEPRECATION")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Appear over the watch face even if the screen is off / locked.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
        }
        peakG = intent.getFloatExtra(EXTRA_PEAK_G, 0f)

        setContent {
            GuardianWatchTheme {
                FallAlertScreen(
                    onImOk = { resolve("fall_cancelled") },
                    onConfirm = { resolve("fall_confirmed") },
                )
            }
        }
    }

    @Suppress("OVERRIDE_DEPRECATION", "MissingSuperCall")
    override fun onBackPressed() {
        // A deliberate swipe/back implies the wearer is conscious and fine.
        resolve("fall_cancelled")
    }

    private fun resolve(kind: String) {
        val repository = applicationContext.graph.repository
        // Detached scope so the POST survives finish(); the foreground service
        // keeps the process alive long enough to complete it.
        CoroutineScope(Dispatchers.IO + SupervisorJob()).launch {
            repository.record(kind, peakG.toDouble())
            runCatching { repository.syncOnce() }
        }
        finish()
    }

    companion object {
        private const val EXTRA_PEAK_G = "peak_g"

        fun intent(context: Context, peakG: Float): Intent =
            Intent(context, FallAlertActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
                .putExtra(EXTRA_PEAK_G, peakG)
    }
}

@Composable
private fun FallAlertScreen(onImOk: () -> Unit, onConfirm: () -> Unit) {
    var remaining by remember { mutableIntStateOf(COUNTDOWN_SEC) }
    LaunchedEffect(Unit) {
        while (remaining > 0) {
            kotlinx.coroutines.delay(1000)
            remaining -= 1
        }
        onConfirm()
    }

    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text("Possible fall", style = MaterialTheme.typography.title3)
            Text(
                "Are you OK?",
                style = MaterialTheme.typography.body1,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(2.dp))
            Text(
                "Alerting in ${remaining}s",
                style = MaterialTheme.typography.caption1,
                color = MaterialTheme.colors.error,
            )
            Spacer(Modifier.height(8.dp))
            Chip(
                onClick = onImOk,
                label = { Text("I'm OK") },
                colors = ChipDefaults.primaryChipColors(),
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(4.dp))
            CompactChip(
                onClick = onConfirm,
                label = { Text("Get help now") },
                colors = ChipDefaults.chipColors(
                    backgroundColor = MaterialTheme.colors.error,
                ),
            )
        }
    }
}
