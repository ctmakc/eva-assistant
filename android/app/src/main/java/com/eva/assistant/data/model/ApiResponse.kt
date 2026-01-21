package com.eva.assistant.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class VoiceResponse(
    val success: Boolean = true,
    @SerialName("recognized_text")
    val recognized_text: String,
    @SerialName("detected_language")
    val detected_language: String = "ru",
    @SerialName("response_text")
    val response_text: String,
    @SerialName("response_audio_url")
    val response_audio_url: String,
    val emotion: String = "neutral"
)

@Serializable
data class ChatRequest(
    val text: String,
    val user_id: String,
    val language: String = "auto"
)

@Serializable
data class ChatResponse(
    val success: Boolean = true,
    @SerialName("response_text")
    val response_text: String,
    @SerialName("response_audio_url")
    val response_audio_url: String? = null,
    val emotion: String = "neutral"
)

@Serializable
data class HealthResponse(
    val status: String,
    val version: String,
    @SerialName("eva_status")
    val eva_status: String = "ready"
)
