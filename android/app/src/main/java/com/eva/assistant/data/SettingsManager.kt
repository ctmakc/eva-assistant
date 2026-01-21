package com.eva.assistant.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.eva.assistant.data.model.Message
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "eva_settings")

class SettingsManager(private val context: Context) {

    companion object {
        val SERVER_URL = stringPreferencesKey("server_url")
        val USER_ID = stringPreferencesKey("user_id")
        val MESSAGES = stringPreferencesKey("messages")
        val MAX_STORED_MESSAGES = stringPreferencesKey("max_stored_messages")

        const val DEFAULT_SERVER_URL = "http://192.168.1.100:8080"
        const val DEFAULT_USER_ID = "android"
        const val DEFAULT_MAX_MESSAGES = 50
    }

    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
    }

    val serverUrl: Flow<String> = context.dataStore.data.map { prefs ->
        prefs[SERVER_URL] ?: DEFAULT_SERVER_URL
    }

    val userId: Flow<String> = context.dataStore.data.map { prefs ->
        prefs[USER_ID] ?: DEFAULT_USER_ID
    }

    suspend fun setServerUrl(url: String) {
        context.dataStore.edit { prefs ->
            prefs[SERVER_URL] = url
        }
    }

    suspend fun setUserId(id: String) {
        context.dataStore.edit { prefs ->
            prefs[USER_ID] = id
        }
    }

    // Message persistence
    suspend fun saveMessages(messages: List<Message>) {
        val maxMessages = context.dataStore.data.first()[MAX_STORED_MESSAGES]?.toIntOrNull()
            ?: DEFAULT_MAX_MESSAGES

        // Keep only last N messages
        val toSave = messages.takeLast(maxMessages)

        val serializable = toSave.map { msg ->
            SerializableMessage(
                id = msg.id,
                text = msg.text,
                isFromUser = msg.isFromUser,
                timestamp = msg.timestamp,
                audioUrl = msg.audioUrl,
                emotion = msg.emotion
            )
        }

        val jsonString = json.encodeToString(serializable)

        context.dataStore.edit { prefs ->
            prefs[MESSAGES] = jsonString
        }
    }

    suspend fun loadMessages(): List<Message> {
        val jsonString = context.dataStore.data.first()[MESSAGES] ?: return emptyList()

        return try {
            val serializable: List<SerializableMessage> = json.decodeFromString(jsonString)
            serializable.map { msg ->
                Message(
                    id = msg.id,
                    text = msg.text,
                    isFromUser = msg.isFromUser,
                    timestamp = msg.timestamp,
                    audioUrl = msg.audioUrl,
                    emotion = msg.emotion
                )
            }
        } catch (e: Exception) {
            emptyList()
        }
    }

    suspend fun clearMessages() {
        context.dataStore.edit { prefs ->
            prefs.remove(MESSAGES)
        }
    }
}

@kotlinx.serialization.Serializable
private data class SerializableMessage(
    val id: String,
    val text: String,
    val isFromUser: Boolean,
    val timestamp: Long,
    val audioUrl: String? = null,
    val emotion: String = "neutral"
)
