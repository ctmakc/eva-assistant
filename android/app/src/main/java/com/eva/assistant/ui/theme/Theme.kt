package com.eva.assistant.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val EvaPrimary = Color(0xFF00D9FF)
val EvaSecondary = Color(0xFF00A8CC)
val EvaBackground = Color(0xFF1A1A2E)
val EvaSurface = Color(0xFF16213E)
val EvaText = Color(0xFFE0E0E0)
val EvaTextSecondary = Color(0xFF888888)

private val DarkColorScheme = darkColorScheme(
    primary = EvaPrimary,
    secondary = EvaSecondary,
    background = EvaBackground,
    surface = EvaSurface,
    onPrimary = Color.Black,
    onSecondary = Color.Black,
    onBackground = EvaText,
    onSurface = EvaText
)

@Composable
fun EvaTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = DarkColorScheme,
        typography = Typography(),
        content = content
    )
}
