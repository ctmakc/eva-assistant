package com.eva.assistant.audio

import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.io.RandomAccessFile

class AudioRecorder(private val context: Context) {

    private var audioRecord: AudioRecord? = null
    private var isRecording = false
    private var recordingThread: Thread? = null

    private val sampleRate = 16000
    private val channelConfig = AudioFormat.CHANNEL_IN_MONO
    private val audioFormat = AudioFormat.ENCODING_PCM_16BIT
    private val bufferSize = AudioRecord.getMinBufferSize(sampleRate, channelConfig, audioFormat)

    fun startRecording(): File? {
        if (isRecording) return null

        val outputFile = File(context.cacheDir, "eva_recording.wav")

        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                sampleRate,
                channelConfig,
                audioFormat,
                bufferSize
            )

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                Log.e("AudioRecorder", "AudioRecord failed to initialize")
                return null
            }

            audioRecord?.startRecording()
            isRecording = true

            recordingThread = Thread {
                writeAudioDataToFile(outputFile)
            }
            recordingThread?.start()

            return outputFile
        } catch (e: SecurityException) {
            Log.e("AudioRecorder", "Permission denied", e)
            return null
        } catch (e: Exception) {
            Log.e("AudioRecorder", "Failed to start recording", e)
            return null
        }
    }

    fun stopRecording(): File? {
        if (!isRecording) return null

        isRecording = false
        audioRecord?.stop()
        audioRecord?.release()
        audioRecord = null

        recordingThread?.join()
        recordingThread = null

        val outputFile = File(context.cacheDir, "eva_recording.wav")
        return if (outputFile.exists()) outputFile else null
    }

    private fun writeAudioDataToFile(outputFile: File) {
        val data = ByteArray(bufferSize)
        val rawFile = File(context.cacheDir, "eva_raw.pcm")

        try {
            FileOutputStream(rawFile).use { os ->
                while (isRecording) {
                    val read = audioRecord?.read(data, 0, bufferSize) ?: 0
                    if (read > 0) {
                        os.write(data, 0, read)
                    }
                }
            }

            // Convert PCM to WAV
            pcmToWav(rawFile, outputFile)
            rawFile.delete()

        } catch (e: Exception) {
            Log.e("AudioRecorder", "Error writing audio", e)
        }
    }

    private fun pcmToWav(pcmFile: File, wavFile: File) {
        val pcmData = pcmFile.readBytes()
        val totalDataLen = pcmData.size + 36
        val byteRate = sampleRate * 1 * 16 / 8

        FileOutputStream(wavFile).use { out ->
            // RIFF header
            out.write("RIFF".toByteArray())
            out.write(intToByteArray(totalDataLen))
            out.write("WAVE".toByteArray())

            // fmt chunk
            out.write("fmt ".toByteArray())
            out.write(intToByteArray(16)) // chunk size
            out.write(shortToByteArray(1)) // audio format (PCM)
            out.write(shortToByteArray(1)) // num channels
            out.write(intToByteArray(sampleRate))
            out.write(intToByteArray(byteRate))
            out.write(shortToByteArray(2)) // block align
            out.write(shortToByteArray(16)) // bits per sample

            // data chunk
            out.write("data".toByteArray())
            out.write(intToByteArray(pcmData.size))
            out.write(pcmData)
        }
    }

    private fun intToByteArray(value: Int): ByteArray {
        return byteArrayOf(
            (value and 0xff).toByte(),
            ((value shr 8) and 0xff).toByte(),
            ((value shr 16) and 0xff).toByte(),
            ((value shr 24) and 0xff).toByte()
        )
    }

    private fun shortToByteArray(value: Int): ByteArray {
        return byteArrayOf(
            (value and 0xff).toByte(),
            ((value shr 8) and 0xff).toByte()
        )
    }
}
