package com.guardian.watch.ui.theme

import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.wear.compose.material.Colors
import androidx.wear.compose.material.MaterialTheme

private val GuardianColors = Colors(
    primary = Color(0xFF2DD4BF),
    onPrimary = Color(0xFF00372F),
    secondary = Color(0xFF5EEAD4),
    surface = Color(0xFF1C2826),
    error = Color(0xFFFF6B6B),
)

@Composable
fun GuardianWatchTheme(content: @Composable () -> Unit) {
    MaterialTheme(colors = GuardianColors, content = content)
}
