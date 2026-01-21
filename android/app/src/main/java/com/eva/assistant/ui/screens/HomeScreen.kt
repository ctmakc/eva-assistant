package com.eva.assistant.ui.screens

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.eva.assistant.data.model.Message
import com.eva.assistant.data.model.UiState
import com.eva.assistant.ui.components.EvaEmotion
import com.eva.assistant.ui.components.EvaFace
import com.eva.assistant.ui.components.RecordButton
import com.eva.assistant.ui.components.StatusText
import com.eva.assistant.ui.theme.EvaBackground
import com.eva.assistant.ui.theme.EvaPrimary
import com.eva.assistant.ui.theme.EvaSurface
import com.eva.assistant.ui.theme.EvaTextSecondary
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    uiState: UiState,
    messages: List<Message>,
    isConnected: Boolean,
    onStartRecording: () -> Unit,
    onStopRecording: () -> Unit,
    onStopPlayback: () -> Unit,
    onSendText: (String) -> Unit,
    onSettingsClick: () -> Unit,
    onClearError: () -> Unit,
    onClearMessages: () -> Unit = {}
) {
    var textInput by remember { mutableStateOf("") }
    val listState = rememberLazyListState()
    val coroutineScope = rememberCoroutineScope()
    var showClearDialog by remember { mutableStateOf(false) }

    // Determine EVA's current emotion from last message
    val currentEmotion = remember(messages, uiState) {
        when (uiState) {
            is UiState.Recording -> EvaEmotion.LISTENING
            is UiState.Processing -> EvaEmotion.THINKING
            is UiState.Playing -> EvaEmotion.SPEAKING
            is UiState.Error -> EvaEmotion.CONCERNED
            else -> {
                // Get emotion from last EVA message
                messages.lastOrNull { !it.isFromUser }?.emotion?.let { emotionStr ->
                    when (emotionStr.lowercase()) {
                        "excited" -> EvaEmotion.EXCITED
                        "supportive" -> EvaEmotion.SUPPORTIVE
                        "playful" -> EvaEmotion.PLAYFUL
                        "concerned" -> EvaEmotion.CONCERNED
                        "calm" -> EvaEmotion.CALM
                        else -> EvaEmotion.FRIENDLY
                    }
                } ?: EvaEmotion.FRIENDLY
            }
        }
    }

    // Auto-scroll to bottom when new message arrives
    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("EVA", style = MaterialTheme.typography.headlineMedium)
                        Spacer(modifier = Modifier.width(8.dp))
                        ConnectionIndicator(isConnected = isConnected)
                    }
                },
                actions = {
                    // Clear chat button
                    if (messages.isNotEmpty()) {
                        IconButton(onClick = { showClearDialog = true }) {
                            Icon(
                                Icons.Default.Delete,
                                contentDescription = "Clear chat",
                                tint = EvaTextSecondary
                            )
                        }
                    }
                    // Settings button
                    IconButton(onClick = onSettingsClick) {
                        Icon(Icons.Default.Settings, contentDescription = "Settings")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = EvaBackground
                )
            )
        },
        containerColor = EvaBackground
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            // Connection warning banner
            AnimatedVisibility(
                visible = !isConnected,
                enter = expandVertically() + fadeIn(),
                exit = shrinkVertically() + fadeOut()
            ) {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = Color(0xFFFF6B6B).copy(alpha = 0.2f)
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            Icons.Default.Warning,
                            contentDescription = null,
                            tint = Color(0xFFFF6B6B),
                            modifier = Modifier.size(20.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            "Нет подключения к серверу. Проверь настройки.",
                            style = MaterialTheme.typography.bodySmall,
                            color = Color(0xFFFF6B6B)
                        )
                    }
                }
            }

            // EVA Face - shows when no messages or few messages
            AnimatedVisibility(
                visible = messages.size < 3,
                enter = fadeIn() + expandVertically(),
                exit = fadeOut() + shrinkVertically()
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    EvaFace(
                        emotion = currentEmotion,
                        isListening = uiState is UiState.Recording,
                        isSpeaking = uiState is UiState.Playing,
                        modifier = Modifier.size(180.dp)
                    )

                    Spacer(modifier = Modifier.height(16.dp))

                    Text(
                        text = when (currentEmotion) {
                            EvaEmotion.LISTENING -> "Слушаю тебя..."
                            EvaEmotion.THINKING -> "Думаю..."
                            EvaEmotion.SPEAKING -> "Говорю..."
                            EvaEmotion.CONCERNED -> "Что-то не так..."
                            else -> if (messages.isEmpty()) "Привет! Нажми на микрофон" else ""
                        },
                        style = MaterialTheme.typography.bodyLarge,
                        color = EvaTextSecondary,
                        textAlign = TextAlign.Center
                    )
                }
            }

            // Mini face for when there are messages
            AnimatedVisibility(
                visible = messages.size >= 3 && (uiState is UiState.Recording || uiState is UiState.Playing || uiState is UiState.Processing),
                enter = fadeIn() + expandVertically(),
                exit = fadeOut() + shrinkVertically()
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(8.dp),
                    contentAlignment = Alignment.Center
                ) {
                    EvaFace(
                        emotion = currentEmotion,
                        isListening = uiState is UiState.Recording,
                        isSpeaking = uiState is UiState.Playing,
                        modifier = Modifier.size(80.dp)
                    )
                }
            }

            // Messages list
            LazyColumn(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp),
                state = listState,
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                item { Spacer(modifier = Modifier.height(8.dp)) }

                items(messages) { message ->
                    MessageBubble(message = message)
                }

                item { Spacer(modifier = Modifier.height(8.dp)) }
            }

            // Record button and status
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                StatusText(uiState = uiState)

                Spacer(modifier = Modifier.height(16.dp))

                RecordButton(
                    uiState = uiState,
                    onStartRecording = onStartRecording,
                    onStopRecording = onStopRecording,
                    onStopPlayback = onStopPlayback
                )

                Spacer(modifier = Modifier.height(16.dp))

                // Text input
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    OutlinedTextField(
                        value = textInput,
                        onValueChange = { textInput = it },
                        modifier = Modifier.weight(1f),
                        placeholder = { Text("Или напиши...", color = EvaTextSecondary) },
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                        keyboardActions = KeyboardActions(
                            onSend = {
                                if (textInput.isNotBlank()) {
                                    onSendText(textInput)
                                    textInput = ""
                                }
                            }
                        ),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = EvaPrimary,
                            unfocusedBorderColor = EvaTextSecondary
                        ),
                        singleLine = true,
                        enabled = isConnected
                    )

                    Spacer(modifier = Modifier.width(8.dp))

                    IconButton(
                        onClick = {
                            if (textInput.isNotBlank()) {
                                onSendText(textInput)
                                textInput = ""
                            }
                        },
                        enabled = textInput.isNotBlank() && uiState is UiState.Idle && isConnected
                    ) {
                        Icon(
                            Icons.Default.Send,
                            contentDescription = "Send",
                            tint = if (textInput.isNotBlank() && isConnected) EvaPrimary else EvaTextSecondary
                        )
                    }
                }
            }
        }
    }

    // Error dialog
    if (uiState is UiState.Error) {
        AlertDialog(
            onDismissRequest = onClearError,
            title = { Text("Ошибка") },
            text = { Text(uiState.message) },
            confirmButton = {
                TextButton(onClick = onClearError) {
                    Text("OK")
                }
            }
        )
    }

    // Clear chat confirmation dialog
    if (showClearDialog) {
        AlertDialog(
            onDismissRequest = { showClearDialog = false },
            title = { Text("Очистить чат?") },
            text = { Text("Все сообщения будут удалены") },
            confirmButton = {
                TextButton(
                    onClick = {
                        onClearMessages()
                        showClearDialog = false
                    }
                ) {
                    Text("Очистить", color = Color(0xFFFF6B6B))
                }
            },
            dismissButton = {
                TextButton(onClick = { showClearDialog = false }) {
                    Text("Отмена")
                }
            }
        )
    }
}

@Composable
fun ConnectionIndicator(isConnected: Boolean) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .background(
                    color = if (isConnected) Color(0xFF4CAF50) else Color(0xFFFF6B6B),
                    shape = RoundedCornerShape(4.dp)
                )
        )
        AnimatedVisibility(
            visible = !isConnected,
            enter = fadeIn() + expandHorizontally(),
            exit = fadeOut() + shrinkHorizontally()
        ) {
            Text(
                text = "offline",
                style = MaterialTheme.typography.labelSmall,
                color = Color(0xFFFF6B6B)
            )
        }
    }
}

@Composable
fun MessageBubble(message: Message) {
    val backgroundColor = if (message.isFromUser) {
        EvaSurface
    } else {
        EvaPrimary.copy(alpha = 0.2f)
    }

    val alignment = if (message.isFromUser) {
        Alignment.End
    } else {
        Alignment.Start
    }

    Box(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = if (message.isFromUser) Alignment.CenterEnd else Alignment.CenterStart
    ) {
        Surface(
            modifier = Modifier.widthIn(max = 300.dp),
            shape = RoundedCornerShape(
                topStart = 16.dp,
                topEnd = 16.dp,
                bottomStart = if (message.isFromUser) 16.dp else 4.dp,
                bottomEnd = if (message.isFromUser) 4.dp else 16.dp
            ),
            color = backgroundColor
        ) {
            Column(modifier = Modifier.padding(12.dp)) {
                if (!message.isFromUser) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = "EVA",
                            style = MaterialTheme.typography.labelSmall,
                            color = EvaPrimary
                        )
                        message.emotion?.let { emotion ->
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = getEmotionEmoji(emotion),
                                style = MaterialTheme.typography.labelSmall
                            )
                        }
                    }
                    Spacer(modifier = Modifier.height(4.dp))
                }
                Text(
                    text = message.text,
                    style = MaterialTheme.typography.bodyMedium
                )
            }
        }
    }
}

private fun getEmotionEmoji(emotion: String): String {
    return when (emotion.lowercase()) {
        "excited" -> "✨"
        "supportive" -> "💙"
        "playful" -> "😊"
        "concerned" -> "🤔"
        "calm" -> "😌"
        "friendly" -> "💫"
        else -> ""
    }
}
