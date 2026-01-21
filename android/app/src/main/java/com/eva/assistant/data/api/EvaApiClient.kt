package com.eva.assistant.data.api

import android.util.Log
import com.eva.assistant.data.model.ChatRequest
import com.eva.assistant.data.model.ChatResponse
import com.eva.assistant.data.model.HealthResponse
import com.eva.assistant.data.model.VoiceResponse
import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.engine.android.*
import io.ktor.client.plugins.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.client.plugins.logging.*
import io.ktor.client.request.*
import io.ktor.client.request.forms.*
import io.ktor.client.statement.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.serialization.json.Json
import java.io.File

class EvaApiClient(private val baseUrl: String) {

    private val client = HttpClient(Android) {
        install(ContentNegotiation) {
            json(Json {
                ignoreUnknownKeys = true
                isLenient = true
            })
        }
        install(HttpTimeout) {
            requestTimeoutMillis = 60000
            connectTimeoutMillis = 10000
            socketTimeoutMillis = 60000
        }
        install(Logging) {
            logger = object : Logger {
                override fun log(message: String) {
                    Log.d("EvaAPI", message)
                }
            }
            level = LogLevel.HEADERS
        }
    }

    suspend fun checkHealth(): Result<HealthResponse> {
        return try {
            val response: HealthResponse = client.get("$baseUrl/api/v1/health").body()
            Result.success(response)
        } catch (e: Exception) {
            Log.e("EvaAPI", "Health check failed", e)
            Result.failure(e)
        }
    }

    suspend fun sendTextMessage(text: String, userId: String = "android"): Result<ChatResponse> {
        return try {
            val response: ChatResponse = client.post("$baseUrl/api/v1/chat/message") {
                contentType(ContentType.Application.Json)
                setBody(ChatRequest(text = text, user_id = userId))
            }.body()
            Result.success(response)
        } catch (e: Exception) {
            Log.e("EvaAPI", "Send message failed", e)
            Result.failure(e)
        }
    }

    suspend fun sendVoice(audioFile: File, userId: String = "android"): Result<VoiceResponse> {
        return try {
            val response: VoiceResponse = client.submitFormWithBinaryData(
                url = "$baseUrl/api/v1/voice/process",
                formData = formData {
                    append("audio", audioFile.readBytes(), Headers.build {
                        append(HttpHeaders.ContentType, "audio/wav")
                        append(HttpHeaders.ContentDisposition, "filename=\"audio.wav\"")
                    })
                    append("user_id", userId)
                }
            ).body()
            Result.success(response)
        } catch (e: Exception) {
            Log.e("EvaAPI", "Send voice failed", e)
            Result.failure(e)
        }
    }

    suspend fun downloadAudio(audioUrl: String): Result<ByteArray> {
        return try {
            val fullUrl = if (audioUrl.startsWith("http")) audioUrl else "$baseUrl$audioUrl"
            val response: HttpResponse = client.get(fullUrl)
            Result.success(response.body())
        } catch (e: Exception) {
            Log.e("EvaAPI", "Download audio failed", e)
            Result.failure(e)
        }
    }

    fun getFullAudioUrl(audioUrl: String): String {
        return if (audioUrl.startsWith("http")) audioUrl else "$baseUrl$audioUrl"
    }

    fun close() {
        client.close()
    }
}
