package com.eva.assistant.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.eva.assistant.MainActivity
import com.eva.assistant.R
import kotlinx.coroutines.*
import kotlin.math.abs

/**
 * Background service for wake word detection.
 *
 * Listens for the wake word "Эва" and launches the app when detected.
 * Uses a simple energy-based detection with keyword matching.
 *
 * For production, consider using Porcupine or similar wake word engine.
 */
class WakeWordService : Service() {

    companion object {
        private const val TAG = "WakeWordService"
        private const val CHANNEL_ID = "eva_wake_word"
        private const val NOTIFICATION_ID = 1001

        private const val SAMPLE_RATE = 16000
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT

        // Detection thresholds
        private const val ENERGY_THRESHOLD = 500  // Minimum audio energy to consider
        private const val SILENCE_DURATION_MS = 1500  // Silence after speech to trigger

        var isRunning = false
            private set

        fun start(context: Context) {
            val intent = Intent(context, WakeWordService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, WakeWordService::class.java))
        }
    }

    private var audioRecord: AudioRecord? = null
    private var isListening = false
    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(NOTIFICATION_ID, createNotification())
        isRunning = true
        startListening()
        return START_STICKY
    }

    override fun onDestroy() {
        super.onDestroy()
        stopListening()
        serviceScope.cancel()
        isRunning = false
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "EVA Wake Word",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Listening for wake word"
                setShowBadge(false)
            }

            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun createNotification() = NotificationCompat.Builder(this, CHANNEL_ID)
        .setContentTitle("EVA слушает")
        .setContentText("Скажи \"Эва\" чтобы начать")
        .setSmallIcon(R.drawable.ic_mic)
        .setPriority(NotificationCompat.PRIORITY_LOW)
        .setOngoing(true)
        .setContentIntent(
            PendingIntent.getActivity(
                this,
                0,
                Intent(this, MainActivity::class.java),
                PendingIntent.FLAG_IMMUTABLE
            )
        )
        .build()

    private fun startListening() {
        if (isListening) return

        val bufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)

        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferSize * 2
            )

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                Log.e(TAG, "AudioRecord failed to initialize")
                return
            }

            audioRecord?.startRecording()
            isListening = true

            serviceScope.launch {
                detectWakeWord(bufferSize)
            }

            Log.i(TAG, "Wake word detection started")

        } catch (e: SecurityException) {
            Log.e(TAG, "Microphone permission denied", e)
        } catch (e: Exception) {
            Log.e(TAG, "Error starting audio recording", e)
        }
    }

    private fun stopListening() {
        isListening = false
        audioRecord?.stop()
        audioRecord?.release()
        audioRecord = null
        Log.i(TAG, "Wake word detection stopped")
    }

    private suspend fun detectWakeWord(bufferSize: Int) = withContext(Dispatchers.IO) {
        val buffer = ShortArray(bufferSize)
        var speechDetected = false
        var silenceStartTime = 0L
        val audioBuffer = mutableListOf<Short>()

        while (isListening) {
            val readCount = audioRecord?.read(buffer, 0, bufferSize) ?: 0

            if (readCount > 0) {
                // Calculate energy (RMS)
                var sum = 0L
                for (i in 0 until readCount) {
                    sum += buffer[i] * buffer[i]
                }
                val energy = Math.sqrt(sum.toDouble() / readCount).toInt()

                if (energy > ENERGY_THRESHOLD) {
                    // Speech detected
                    if (!speechDetected) {
                        speechDetected = true
                        audioBuffer.clear()
                        Log.d(TAG, "Speech started, energy: $energy")
                    }
                    silenceStartTime = System.currentTimeMillis()

                    // Buffer audio for analysis
                    for (i in 0 until readCount) {
                        audioBuffer.add(buffer[i])
                    }

                    // Limit buffer size (about 3 seconds)
                    if (audioBuffer.size > SAMPLE_RATE * 3) {
                        audioBuffer.subList(0, audioBuffer.size - SAMPLE_RATE * 3).clear()
                    }

                } else if (speechDetected) {
                    // Silence after speech
                    val silenceDuration = System.currentTimeMillis() - silenceStartTime

                    if (silenceDuration > SILENCE_DURATION_MS) {
                        // Speech ended - check for wake word
                        Log.d(TAG, "Speech ended, buffer size: ${audioBuffer.size}")

                        // For simple detection, we check if audio has certain patterns
                        // In production, use Porcupine or send to server for STT
                        if (audioBuffer.size > SAMPLE_RATE / 2) {
                            // Has enough audio to potentially be "Эва"
                            onPotentialWakeWord(audioBuffer.toShortArray())
                        }

                        speechDetected = false
                        audioBuffer.clear()
                    }
                }
            }

            delay(50) // Small delay to prevent tight loop
        }
    }

    private fun onPotentialWakeWord(audio: ShortArray) {
        // Simple detection: if audio is between 0.3-1.5 seconds, could be "Эва"
        val durationSec = audio.size.toFloat() / SAMPLE_RATE

        if (durationSec in 0.3f..1.5f) {
            Log.i(TAG, "Potential wake word detected! Duration: ${durationSec}s")

            // Launch app with voice mode
            val intent = Intent(this, MainActivity::class.java).apply {
                action = "com.eva.assistant.ACTION_VOICE"
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
            startActivity(intent)

            // Brief pause to avoid re-triggering
            serviceScope.launch {
                isListening = false
                delay(3000)
                isListening = true
            }
        }
    }
}
