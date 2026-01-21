package com.eva.assistant.data.model

import java.util.UUID

data class Message(
    val id: String = UUID.randomUUID().toString(),
    val text: String,
    val isFromUser: Boolean,
    val timestamp: Long = System.currentTimeMillis(),
    val audioUrl: String? = null,
    val emotion: String = "neutral"
)
