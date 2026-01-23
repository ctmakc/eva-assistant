package com.eva.assistant.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.eva.assistant.service.WakeWordService
import com.eva.assistant.ui.theme.EvaBackground
import com.eva.assistant.ui.theme.EvaPrimary

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    serverUrl: String,
    userId: String,
    isConnected: Boolean,
    wakeWordEnabled: Boolean = false,
    onServerUrlChange: (String) -> Unit,
    onUserIdChange: (String) -> Unit,
    onCheckConnection: () -> Unit,
    onWakeWordChange: (Boolean) -> Unit = {},
    onBackClick: () -> Unit
) {
    val context = LocalContext.current
    var urlInput by remember(serverUrl) { mutableStateOf(serverUrl) }
    var userIdInput by remember(userId) { mutableStateOf(userId) }
    var wakeWordState by remember { mutableStateOf(WakeWordService.isRunning) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Настройки") },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
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
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Connection status
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = if (isConnected) {
                        Color.Green.copy(alpha = 0.1f)
                    } else {
                        Color.Red.copy(alpha = 0.1f)
                    }
                )
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(12.dp)
                            .padding(end = 8.dp)
                    ) {
                        Icon(
                            Icons.Default.Check,
                            contentDescription = null,
                            tint = if (isConnected) Color.Green else Color.Red,
                            modifier = Modifier.size(12.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (isConnected) "Подключено к серверу" else "Нет подключения",
                        style = MaterialTheme.typography.bodyLarge
                    )
                    Spacer(modifier = Modifier.weight(1f))
                    IconButton(onClick = onCheckConnection) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh")
                    }
                }
            }

            // Server URL
            OutlinedTextField(
                value = urlInput,
                onValueChange = { urlInput = it },
                label = { Text("Адрес сервера") },
                placeholder = { Text("http://192.168.1.100:8080") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = EvaPrimary
                )
            )

            // User ID
            OutlinedTextField(
                value = userIdInput,
                onValueChange = { userIdInput = it },
                label = { Text("Имя пользователя") },
                placeholder = { Text("android") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = EvaPrimary
                )
            )

            Spacer(modifier = Modifier.height(8.dp))

            // Save button
            Button(
                onClick = {
                    onServerUrlChange(urlInput)
                    onUserIdChange(userIdInput)
                    onCheckConnection()
                },
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = EvaPrimary)
            ) {
                Text("Сохранить", color = Color.Black)
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Wake Word Section
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = Color.White.copy(alpha = 0.05f)
                )
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Голосовая активация",
                            style = MaterialTheme.typography.bodyLarge
                        )
                        Text(
                            text = "Скажи \"Эва\" чтобы активировать",
                            style = MaterialTheme.typography.bodySmall,
                            color = Color.Gray
                        )
                    }
                    Switch(
                        checked = wakeWordState,
                        onCheckedChange = { enabled ->
                            wakeWordState = enabled
                            if (enabled) {
                                WakeWordService.start(context)
                            } else {
                                WakeWordService.stop(context)
                            }
                            onWakeWordChange(enabled)
                        },
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = EvaPrimary,
                            checkedTrackColor = EvaPrimary.copy(alpha = 0.5f)
                        )
                    )
                }
            }

            if (wakeWordState) {
                Text(
                    text = "⚡ EVA слушает в фоне. Скажи \"Эва\" чтобы начать разговор.",
                    style = MaterialTheme.typography.bodySmall,
                    color = EvaPrimary,
                    modifier = Modifier.padding(horizontal = 4.dp)
                )
            }

            Spacer(modifier = Modifier.weight(1f))

            // Help text
            Text(
                text = "Введи адрес сервера EVA.\n" +
                        "Например: http://192.168.1.100:8080\n\n" +
                        "Убедись что телефон и сервер в одной сети.",
                style = MaterialTheme.typography.bodySmall,
                color = Color.Gray
            )
        }
    }
}
