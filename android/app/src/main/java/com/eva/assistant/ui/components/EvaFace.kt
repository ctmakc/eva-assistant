package com.eva.assistant.ui.components

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Fill
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import kotlin.math.sin
import kotlin.random.Random

enum class EvaEmotion {
    FRIENDLY,
    EXCITED,
    SUPPORTIVE,
    PLAYFUL,
    CONCERNED,
    CALM,
    LISTENING,
    THINKING,
    SPEAKING
}

@Composable
fun EvaFace(
    emotion: EvaEmotion = EvaEmotion.FRIENDLY,
    isListening: Boolean = false,
    isSpeaking: Boolean = false,
    modifier: Modifier = Modifier
) {
    // Determine actual emotion based on state
    val currentEmotion = when {
        isListening -> EvaEmotion.LISTENING
        isSpeaking -> EvaEmotion.SPEAKING
        else -> emotion
    }

    // Blink animation
    var isBlinking by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        while (true) {
            delay(Random.nextLong(2000, 5000))
            isBlinking = true
            delay(150)
            isBlinking = false
        }
    }

    // Eye movement animation
    val infiniteTransition = rememberInfiniteTransition(label = "eyeMovement")
    val eyeOffsetX by infiniteTransition.animateFloat(
        initialValue = -1f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(3000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "eyeX"
    )
    val eyeOffsetY by infiniteTransition.animateFloat(
        initialValue = -0.5f,
        targetValue = 0.5f,
        animationSpec = infiniteRepeatable(
            animation = tween(2500, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "eyeY"
    )

    // Breathing animation for the face
    val breathe by infiniteTransition.animateFloat(
        initialValue = 0.98f,
        targetValue = 1.02f,
        animationSpec = infiniteRepeatable(
            animation = tween(2000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "breathe"
    )

    // Speaking animation
    val speakingAnim by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(200, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "speaking"
    )

    // Listening pulse animation
    val listeningPulse by infiniteTransition.animateFloat(
        initialValue = 0.9f,
        targetValue = 1.1f,
        animationSpec = infiniteRepeatable(
            animation = tween(500, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "listening"
    )

    // Excited bounce
    val excitedBounce by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 10f,
        animationSpec = infiniteRepeatable(
            animation = tween(300, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "excited"
    )

    // Colors
    val faceColor = Color(0xFF1A1A2E)
    val eyeColor = Color(0xFF00D9FF)
    val glowColor = Color(0xFF00D9FF).copy(alpha = 0.3f)
    val mouthColor = Color(0xFF00D9FF)

    Box(
        modifier = modifier.size(200.dp),
        contentAlignment = Alignment.Center
    ) {
        Canvas(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp)
        ) {
            val centerX = size.width / 2
            val centerY = size.height / 2
            val faceRadius = size.minDimension / 2 * breathe

            // Apply bounce for excited emotion
            val bounceOffset = if (currentEmotion == EvaEmotion.EXCITED) excitedBounce else 0f

            // Face background (circle with glow)
            drawCircle(
                color = glowColor,
                radius = faceRadius * 1.1f,
                center = Offset(centerX, centerY - bounceOffset)
            )
            drawCircle(
                color = faceColor,
                radius = faceRadius,
                center = Offset(centerX, centerY - bounceOffset)
            )
            drawCircle(
                color = eyeColor.copy(alpha = 0.5f),
                radius = faceRadius,
                center = Offset(centerX, centerY - bounceOffset),
                style = Stroke(width = 3f)
            )

            // Eye positions
            val eyeSpacing = faceRadius * 0.4f
            val eyeY = centerY - faceRadius * 0.15f - bounceOffset
            val leftEyeX = centerX - eyeSpacing
            val rightEyeX = centerX + eyeSpacing
            val eyeRadius = faceRadius * 0.18f

            // Pupil offset based on animation and emotion
            val pupilOffsetX = eyeOffsetX * eyeRadius * 0.3f
            val pupilOffsetY = eyeOffsetY * eyeRadius * 0.2f

            // Apply listening pulse
            val eyeScale = if (currentEmotion == EvaEmotion.LISTENING) listeningPulse else 1f

            // Draw eyes based on emotion
            when {
                isBlinking -> {
                    // Closed eyes (lines)
                    drawLine(
                        color = eyeColor,
                        start = Offset(leftEyeX - eyeRadius, eyeY),
                        end = Offset(leftEyeX + eyeRadius, eyeY),
                        strokeWidth = 4f
                    )
                    drawLine(
                        color = eyeColor,
                        start = Offset(rightEyeX - eyeRadius, eyeY),
                        end = Offset(rightEyeX + eyeRadius, eyeY),
                        strokeWidth = 4f
                    )
                }
                currentEmotion == EvaEmotion.PLAYFUL -> {
                    // Winking/playful eyes (one ^ one O)
                    // Left eye - wink
                    drawLine(
                        color = eyeColor,
                        start = Offset(leftEyeX - eyeRadius * 0.7f, eyeY),
                        end = Offset(leftEyeX, eyeY - eyeRadius * 0.5f),
                        strokeWidth = 4f
                    )
                    drawLine(
                        color = eyeColor,
                        start = Offset(leftEyeX, eyeY - eyeRadius * 0.5f),
                        end = Offset(leftEyeX + eyeRadius * 0.7f, eyeY),
                        strokeWidth = 4f
                    )
                    // Right eye - normal
                    drawEye(rightEyeX, eyeY, eyeRadius * eyeScale, pupilOffsetX, pupilOffsetY, eyeColor)
                }
                currentEmotion == EvaEmotion.CONCERNED -> {
                    // Worried eyes (tilted eyebrows implied by oval shape)
                    drawOval(
                        color = eyeColor,
                        topLeft = Offset(leftEyeX - eyeRadius, eyeY - eyeRadius * 0.6f),
                        size = Size(eyeRadius * 2, eyeRadius * 1.2f),
                        style = Stroke(width = 3f)
                    )
                    drawOval(
                        color = eyeColor,
                        topLeft = Offset(rightEyeX - eyeRadius, eyeY - eyeRadius * 0.6f),
                        size = Size(eyeRadius * 2, eyeRadius * 1.2f),
                        style = Stroke(width = 3f)
                    )
                    // Pupils
                    drawCircle(
                        color = eyeColor,
                        radius = eyeRadius * 0.3f,
                        center = Offset(leftEyeX + pupilOffsetX, eyeY + pupilOffsetY)
                    )
                    drawCircle(
                        color = eyeColor,
                        radius = eyeRadius * 0.3f,
                        center = Offset(rightEyeX + pupilOffsetX, eyeY + pupilOffsetY)
                    )
                }
                currentEmotion == EvaEmotion.EXCITED -> {
                    // Big sparkly eyes
                    drawEye(leftEyeX, eyeY, eyeRadius * 1.2f, pupilOffsetX, pupilOffsetY, eyeColor)
                    drawEye(rightEyeX, eyeY, eyeRadius * 1.2f, pupilOffsetX, pupilOffsetY, eyeColor)
                    // Sparkles
                    drawLine(eyeColor, Offset(leftEyeX - eyeRadius * 1.5f, eyeY - eyeRadius), Offset(leftEyeX - eyeRadius * 1.8f, eyeY - eyeRadius * 0.7f), 2f)
                    drawLine(eyeColor, Offset(rightEyeX + eyeRadius * 1.5f, eyeY - eyeRadius), Offset(rightEyeX + eyeRadius * 1.8f, eyeY - eyeRadius * 0.7f), 2f)
                }
                currentEmotion == EvaEmotion.CALM -> {
                    // Relaxed half-closed eyes
                    drawArc(
                        color = eyeColor,
                        startAngle = 0f,
                        sweepAngle = 180f,
                        useCenter = false,
                        topLeft = Offset(leftEyeX - eyeRadius, eyeY - eyeRadius * 0.3f),
                        size = Size(eyeRadius * 2, eyeRadius),
                        style = Stroke(width = 3f)
                    )
                    drawArc(
                        color = eyeColor,
                        startAngle = 0f,
                        sweepAngle = 180f,
                        useCenter = false,
                        topLeft = Offset(rightEyeX - eyeRadius, eyeY - eyeRadius * 0.3f),
                        size = Size(eyeRadius * 2, eyeRadius),
                        style = Stroke(width = 3f)
                    )
                }
                currentEmotion == EvaEmotion.THINKING -> {
                    // Looking up eyes
                    drawEye(leftEyeX, eyeY, eyeRadius * eyeScale, eyeRadius * 0.2f, -eyeRadius * 0.4f, eyeColor)
                    drawEye(rightEyeX, eyeY, eyeRadius * eyeScale, eyeRadius * 0.2f, -eyeRadius * 0.4f, eyeColor)
                }
                else -> {
                    // Normal eyes
                    drawEye(leftEyeX, eyeY, eyeRadius * eyeScale, pupilOffsetX, pupilOffsetY, eyeColor)
                    drawEye(rightEyeX, eyeY, eyeRadius * eyeScale, pupilOffsetX, pupilOffsetY, eyeColor)
                }
            }

            // Mouth position
            val mouthY = centerY + faceRadius * 0.35f - bounceOffset
            val mouthWidth = faceRadius * 0.5f

            // Draw mouth based on emotion
            when (currentEmotion) {
                EvaEmotion.FRIENDLY, EvaEmotion.SUPPORTIVE -> {
                    // Gentle smile
                    drawArc(
                        color = mouthColor,
                        startAngle = 20f,
                        sweepAngle = 140f,
                        useCenter = false,
                        topLeft = Offset(centerX - mouthWidth, mouthY - mouthWidth * 0.3f),
                        size = Size(mouthWidth * 2, mouthWidth * 0.8f),
                        style = Stroke(width = 4f)
                    )
                }
                EvaEmotion.EXCITED -> {
                    // Big open smile
                    val path = Path().apply {
                        moveTo(centerX - mouthWidth, mouthY)
                        quadraticBezierTo(centerX, mouthY + mouthWidth * 0.8f, centerX + mouthWidth, mouthY)
                        quadraticBezierTo(centerX, mouthY + mouthWidth * 0.3f, centerX - mouthWidth, mouthY)
                    }
                    drawPath(path, mouthColor, style = Fill)
                }
                EvaEmotion.PLAYFUL -> {
                    // Cheeky grin
                    drawArc(
                        color = mouthColor,
                        startAngle = 10f,
                        sweepAngle = 160f,
                        useCenter = false,
                        topLeft = Offset(centerX - mouthWidth * 0.8f, mouthY - mouthWidth * 0.2f),
                        size = Size(mouthWidth * 1.6f, mouthWidth * 0.7f),
                        style = Stroke(width = 4f)
                    )
                    // Tongue or dimple
                    drawCircle(mouthColor, mouthWidth * 0.1f, Offset(centerX + mouthWidth * 0.5f, mouthY + mouthWidth * 0.15f))
                }
                EvaEmotion.CONCERNED -> {
                    // Worried frown (slight downward curve)
                    drawArc(
                        color = mouthColor,
                        startAngle = 200f,
                        sweepAngle = 140f,
                        useCenter = false,
                        topLeft = Offset(centerX - mouthWidth * 0.6f, mouthY),
                        size = Size(mouthWidth * 1.2f, mouthWidth * 0.4f),
                        style = Stroke(width = 4f)
                    )
                }
                EvaEmotion.CALM -> {
                    // Serene slight smile
                    drawArc(
                        color = mouthColor,
                        startAngle = 30f,
                        sweepAngle = 120f,
                        useCenter = false,
                        topLeft = Offset(centerX - mouthWidth * 0.5f, mouthY - mouthWidth * 0.15f),
                        size = Size(mouthWidth, mouthWidth * 0.4f),
                        style = Stroke(width = 3f)
                    )
                }
                EvaEmotion.LISTENING -> {
                    // Small 'o' mouth (attentive)
                    drawOval(
                        color = mouthColor,
                        topLeft = Offset(centerX - mouthWidth * 0.2f, mouthY - mouthWidth * 0.15f),
                        size = Size(mouthWidth * 0.4f, mouthWidth * 0.3f * listeningPulse),
                        style = Stroke(width = 3f)
                    )
                }
                EvaEmotion.SPEAKING -> {
                    // Animated speaking mouth
                    val mouthOpenness = mouthWidth * 0.2f + mouthWidth * 0.3f * speakingAnim
                    drawOval(
                        color = mouthColor,
                        topLeft = Offset(centerX - mouthWidth * 0.4f, mouthY - mouthOpenness / 2),
                        size = Size(mouthWidth * 0.8f, mouthOpenness),
                        style = Fill
                    )
                }
                EvaEmotion.THINKING -> {
                    // Hmm mouth (small line with slight upturn)
                    drawLine(
                        color = mouthColor,
                        start = Offset(centerX - mouthWidth * 0.3f, mouthY),
                        end = Offset(centerX + mouthWidth * 0.3f, mouthY - mouthWidth * 0.05f),
                        strokeWidth = 4f
                    )
                }
            }

            // Add blush for supportive/friendly emotions
            if (currentEmotion == EvaEmotion.SUPPORTIVE || currentEmotion == EvaEmotion.FRIENDLY) {
                drawCircle(
                    color = Color(0xFFFF6B9D).copy(alpha = 0.3f),
                    radius = eyeRadius * 0.6f,
                    center = Offset(leftEyeX - eyeRadius * 0.8f, eyeY + eyeRadius * 1.2f)
                )
                drawCircle(
                    color = Color(0xFFFF6B9D).copy(alpha = 0.3f),
                    radius = eyeRadius * 0.6f,
                    center = Offset(rightEyeX + eyeRadius * 0.8f, eyeY + eyeRadius * 1.2f)
                )
            }
        }
    }
}

private fun DrawScope.drawEye(
    x: Float,
    y: Float,
    radius: Float,
    pupilOffsetX: Float,
    pupilOffsetY: Float,
    color: Color
) {
    // Eye outline
    drawCircle(
        color = color,
        radius = radius,
        center = Offset(x, y),
        style = Stroke(width = 3f)
    )
    // Pupil
    drawCircle(
        color = color,
        radius = radius * 0.4f,
        center = Offset(x + pupilOffsetX, y + pupilOffsetY)
    )
    // Highlight
    drawCircle(
        color = Color.White.copy(alpha = 0.6f),
        radius = radius * 0.15f,
        center = Offset(x + pupilOffsetX - radius * 0.2f, y + pupilOffsetY - radius * 0.2f)
    )
}
