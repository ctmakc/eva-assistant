package com.eva.assistant.ui

import android.app.Application
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.eva.assistant.audio.AudioPlayer
import com.eva.assistant.audio.AudioRecorder
import com.eva.assistant.data.SettingsManager
import com.eva.assistant.data.api.EvaApiClient
import com.eva.assistant.data.model.Message
import com.eva.assistant.data.model.UiState
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.io.File

class EvaViewModel(application: Application) : AndroidViewModel(application) {

    private val settingsManager = SettingsManager(application)
    private val audioRecorder = AudioRecorder(application)
    private val audioPlayer = AudioPlayer(application)

    private var apiClient: EvaApiClient? = null
    private var recordingFile: File? = null

    private val _uiState = MutableStateFlow<UiState>(UiState.Idle)
    val uiState: StateFlow<UiState> = _uiState

    private val _messages = MutableStateFlow<List<Message>>(emptyList())
    val messages: StateFlow<List<Message>> = _messages

    private val _serverUrl = MutableStateFlow(SettingsManager.DEFAULT_SERVER_URL)
    val serverUrl: StateFlow<String> = _serverUrl

    private val _userId = MutableStateFlow(SettingsManager.DEFAULT_USER_ID)
    val userId: StateFlow<String> = _userId

    private val _isConnected = MutableStateFlow(false)
    val isConnected: StateFlow<Boolean> = _isConnected

    val isPlaying: StateFlow<Boolean> = audioPlayer.isPlaying

    init {
        viewModelScope.launch {
            settingsManager.serverUrl.collect { url ->
                _serverUrl.value = url
                reconnect()
            }
        }
        viewModelScope.launch {
            settingsManager.userId.collect { id ->
                _userId.value = id
            }
        }
    }

    private fun reconnect() {
        apiClient?.close()
        apiClient = EvaApiClient(_serverUrl.value)
        checkConnection()
    }

    fun checkConnection() {
        viewModelScope.launch {
            val client = apiClient ?: return@launch
            val result = client.checkHealth()
            _isConnected.value = result.isSuccess
        }
    }

    fun updateServerUrl(url: String) {
        viewModelScope.launch {
            settingsManager.setServerUrl(url)
        }
    }

    fun updateUserId(id: String) {
        viewModelScope.launch {
            settingsManager.setUserId(id)
        }
    }

    fun startRecording() {
        if (_uiState.value != UiState.Idle) return

        recordingFile = audioRecorder.startRecording()
        if (recordingFile != null) {
            _uiState.value = UiState.Recording
        } else {
            _uiState.value = UiState.Error("Не удалось начать запись")
        }
    }

    fun stopRecording() {
        if (_uiState.value != UiState.Recording) return

        val file = audioRecorder.stopRecording()
        if (file != null && file.exists()) {
            _uiState.value = UiState.Processing
            sendVoice(file)
        } else {
            _uiState.value = UiState.Error("Запись не удалась")
        }
    }

    private fun sendVoice(file: File) {
        viewModelScope.launch {
            val client = apiClient
            if (client == null) {
                _uiState.value = UiState.Error("Не подключен к серверу")
                return@launch
            }

            val result = client.sendVoice(file, _userId.value)
            result.onSuccess { response ->
                // Add user message
                _messages.value = _messages.value + Message(
                    text = response.recognized_text,
                    isFromUser = true
                )

                // Add EVA response
                val audioUrl = client.getFullAudioUrl(response.response_audio_url)
                _messages.value = _messages.value + Message(
                    text = response.response_text,
                    isFromUser = false,
                    audioUrl = audioUrl,
                    emotion = response.emotion
                )

                // Play response
                playAudio(audioUrl)

            }.onFailure { error ->
                Log.e("EvaViewModel", "Voice send failed", error)
                _uiState.value = UiState.Error("Ошибка: ${error.localizedMessage ?: "Неизвестная ошибка"}")
            }

            file.delete()
        }
    }

    fun sendTextMessage(text: String) {
        if (text.isBlank()) return

        _uiState.value = UiState.Processing

        // Add user message immediately
        _messages.value = _messages.value + Message(
            text = text,
            isFromUser = true
        )

        viewModelScope.launch {
            val client = apiClient
            if (client == null) {
                _uiState.value = UiState.Error("Не подключен к серверу")
                return@launch
            }

            val result = client.sendTextMessage(text, _userId.value)
            result.onSuccess { response ->
                val audioUrl = response.response_audio_url?.let { client.getFullAudioUrl(it) }

                _messages.value = _messages.value + Message(
                    text = response.response_text,
                    isFromUser = false,
                    audioUrl = audioUrl,
                    emotion = response.emotion
                )

                // Play response if audio available
                audioUrl?.let { playAudio(it) } ?: run {
                    _uiState.value = UiState.Idle
                }

            }.onFailure { error ->
                Log.e("EvaViewModel", "Text send failed", error)
                _uiState.value = UiState.Error("Ошибка: ${error.localizedMessage ?: "Неизвестная ошибка"}")
            }
        }
    }

    private fun playAudio(url: String) {
        _uiState.value = UiState.Playing
        audioPlayer.play(url)

        viewModelScope.launch {
            audioPlayer.isPlaying.collect { isPlaying ->
                if (!isPlaying && _uiState.value == UiState.Playing) {
                    _uiState.value = UiState.Idle
                }
            }
        }
    }

    fun stopPlayback() {
        audioPlayer.stop()
        _uiState.value = UiState.Idle
    }

    fun clearError() {
        _uiState.value = UiState.Idle
    }

    fun clearMessages() {
        _messages.value = emptyList()
    }

    override fun onCleared() {
        super.onCleared()
        apiClient?.close()
        audioPlayer.release()
    }
}
