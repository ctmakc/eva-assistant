package com.eva.assistant.data.model

sealed class UiState {
    object Idle : UiState()
    object Recording : UiState()
    object Processing : UiState()
    object Playing : UiState()
    data class Error(val message: String) : UiState()
}
