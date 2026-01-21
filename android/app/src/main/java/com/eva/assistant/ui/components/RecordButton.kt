package com.eva.assistant.ui.components

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import com.eva.assistant.data.model.UiState
import com.eva.assistant.ui.theme.EvaPrimary
import com.eva.assistant.ui.theme.EvaSecondary

@Composable
fun RecordButton(
    uiState: UiState,
    onStartRecording: () -> Unit,
    onStopRecording: () -> Unit,
    onStopPlayback: () -> Unit,
    modifier: Modifier = Modifier
) {
    val isRecording = uiState is UiState.Recording
    val isProcessing = uiState is UiState.Processing
    val isPlaying = uiState is UiState.Playing

    // Pulse animation for recording
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val pulseScale by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 1.2f,
        animationSpec = infiniteRepeatable(
            animation = tween(600),
            repeatMode = RepeatMode.Reverse
        ),
        label = "scale"
    )

    // Rotation for processing
    val rotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(1000, easing = LinearEasing)
        ),
        label = "rotation"
    )

    Box(
        modifier = modifier,
        contentAlignment = Alignment.Center
    ) {
        // Outer glow when recording
        if (isRecording) {
            Box(
                modifier = Modifier
                    .size(140.dp)
                    .scale(pulseScale)
                    .background(
                        brush = Brush.radialGradient(
                            colors = listOf(
                                EvaPrimary.copy(alpha = 0.3f),
                                Color.Transparent
                            )
                        ),
                        shape = CircleShape
                    )
            )
        }

        // Main button
        Button(
            onClick = {
                when {
                    isRecording -> onStopRecording()
                    isPlaying -> onStopPlayback()
                    !isProcessing -> onStartRecording()
                }
            },
            modifier = Modifier.size(100.dp),
            shape = CircleShape,
            colors = ButtonDefaults.buttonColors(
                containerColor = when {
                    isRecording -> Color.Red.copy(alpha = 0.8f)
                    isProcessing -> EvaSecondary
                    isPlaying -> EvaPrimary.copy(alpha = 0.7f)
                    else -> EvaPrimary
                }
            ),
            enabled = !isProcessing
        ) {
            when {
                isProcessing -> {
                    CircularProgressIndicator(
                        modifier = Modifier.size(40.dp),
                        color = Color.White,
                        strokeWidth = 3.dp
                    )
                }
                isRecording -> {
                    Icon(
                        imageVector = Icons.Default.Stop,
                        contentDescription = "Stop recording",
                        modifier = Modifier.size(40.dp),
                        tint = Color.White
                    )
                }
                isPlaying -> {
                    Icon(
                        imageVector = Icons.Default.Stop,
                        contentDescription = "Stop playback",
                        modifier = Modifier.size(40.dp),
                        tint = Color.White
                    )
                }
                else -> {
                    Icon(
                        imageVector = Icons.Default.Mic,
                        contentDescription = "Start recording",
                        modifier = Modifier.size(40.dp),
                        tint = Color.Black
                    )
                }
            }
        }
    }
}

@Composable
fun StatusText(uiState: UiState) {
    val text = when (uiState) {
        is UiState.Idle -> "Нажми для записи"
        is UiState.Recording -> "Записываю..."
        is UiState.Processing -> "Думаю..."
        is UiState.Playing -> "Говорю..."
        is UiState.Error -> uiState.message
    }

    val color = when (uiState) {
        is UiState.Error -> Color.Red
        is UiState.Recording -> EvaPrimary
        else -> EvaSecondary
    }

    Text(
        text = text,
        color = color,
        style = MaterialTheme.typography.bodyLarge
    )
}
