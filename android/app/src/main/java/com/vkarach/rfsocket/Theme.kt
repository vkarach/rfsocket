package com.vkarach.rfsocket

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

object Palette {
    val Background = Color(0xFF0E1116)
    val BackgroundTop = Color(0xFF161B22)
    val Surface = Color(0xFF1B212B)
    val Outline = Color(0xFF2C3440)
    val Muted = Color(0xFF8B95A5)
    val Text = Color(0xFFE6EAF0)
    val Amber = Color(0xFFFFB547)
    val Orange = Color(0xFFFF8A3D)
    val OnAmber = Color(0xFF2A1A05)
    val Error = Color(0xFFFF6B6B)
}

@Composable
fun RfSocketTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Palette.Amber,
            onPrimary = Palette.OnAmber,
            background = Palette.Background,
            surface = Palette.Surface,
            onBackground = Palette.Text,
            onSurface = Palette.Text,
            error = Palette.Error,
        ),
        content = content,
    )
}
