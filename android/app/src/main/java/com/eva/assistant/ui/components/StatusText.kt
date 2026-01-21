package com.eva.assistant.ui.components

import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.eva.assistant.data.model.UiState
import com.eva.assistant.ui.theme.EvaPrimary
import com.eva.assistant.ui.theme.EvaTextSecondary

@Composable
fun StatusText(
    uiState: UiState,
    modifier: Modifier = Modifier
) {
    AnimatedContent(
        targetState = uiState,
        transitionSpec = {
            fadeIn() + slideInVertically() togetherWith fadeOut() + slideOutVertically()
        },
        modifier = modifier,
        label = "statusAnimation"
    ) { state ->
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center
        ) {
            when (state) {
                is UiState.Idle -> {
                    // No text when idle
                }
                is UiState.Recording -> {
                    PulsingDot()
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Слушаю...",
                        style = MaterialTheme.typography.bodyMedium,
                        color = EvaPrimary
                    )
                }
                is UiState.Processing -> {
                    CircularProgressIndicator(
                        modifier = Modifier.size(16.dp),
                        strokeWidth = 2.dp,
                        color = EvaPrimary
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Обрабатываю...",
                        style = MaterialTheme.typography.bodyMedium,
                        color = EvaTextSecondary
                    )
                }
                is UiState.Playing -> {
                    SoundWaveIndicator()
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Говорю...",
                        style = MaterialTheme.typography.bodyMedium,
                        color = EvaPrimary
                    )
                }
                is UiState.Error -> {
                    Text(
                        text = "Ошибка",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.error
                    )
                }
            }
        }
    }
}

@Composable
private fun PulsingDot() {
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val alpha by infiniteTransition.animateFloat(
        initialValue = 0.3f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(500),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulseAlpha"
    )

    Box(
        modifier = Modifier
            .size(12.dp)
            .background(
                color = EvaPrimary.copy(alpha = alpha),
                shape = CircleShape
            )
    )
}

@Composable
private fun SoundWaveIndicator() {
    val infiniteTransition = rememberInfiniteTransition(label = "soundWave")

    Row(
        horizontalArrangement = Arrangement.spacedBy(2.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        repeat(3) { index ->
            val height by infiniteTransition.animateFloat(
                initialValue = 4f,
                targetValue = 12f,
                animationSpec = infiniteRepeatable(
                    animation = tween(300, delayMillis = index * 100),
                    repeatMode = RepeatMode.Reverse
                ),
                label = "bar$index"
            )

            Box(
                modifier = Modifier
                    .width(3.dp)
                    .height(height.dp)
                    .background(
                        color = EvaPrimary,
                        shape = RoundedCornerShape(1.dp)
                    )
            )
        }
    }
}
