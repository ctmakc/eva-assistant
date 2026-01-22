package com.eva.assistant

import android.Manifest
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.eva.assistant.ui.EvaViewModel
import com.eva.assistant.ui.screens.HomeScreen
import com.eva.assistant.ui.screens.SettingsScreen
import com.eva.assistant.ui.theme.EvaTheme
import com.eva.assistant.widget.EvaWidget
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.isGranted
import com.google.accompanist.permissions.rememberPermissionState
import com.google.accompanist.permissions.shouldShowRationale

class MainActivity : ComponentActivity() {
    // Track if we should start recording (from widget)
    private var startVoiceMode = false

    @OptIn(ExperimentalPermissionsApi::class)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Check if opened from widget with voice action
        startVoiceMode = intent?.action == EvaWidget.ACTION_VOICE

        setContent {
            EvaTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val micPermissionState = rememberPermissionState(Manifest.permission.RECORD_AUDIO)

                    LaunchedEffect(Unit) {
                        if (!micPermissionState.status.isGranted) {
                            micPermissionState.launchPermissionRequest()
                        }
                    }

                    EvaApp(startVoiceMode = startVoiceMode)
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        // Handle widget click when app is already running
        if (intent.action == EvaWidget.ACTION_VOICE) {
            startVoiceMode = true
        }
    }
}

@Composable
fun EvaApp(startVoiceMode: Boolean = false) {
    val navController = rememberNavController()
    val viewModel: EvaViewModel = viewModel()

    val uiState by viewModel.uiState.collectAsState()
    val messages by viewModel.messages.collectAsState()
    val serverUrl by viewModel.serverUrl.collectAsState()
    val userId by viewModel.userId.collectAsState()
    val isConnected by viewModel.isConnected.collectAsState()

    // Auto-start recording if opened from widget
    var hasStartedVoice by remember { mutableStateOf(false) }
    LaunchedEffect(startVoiceMode, isConnected) {
        if (startVoiceMode && isConnected && !hasStartedVoice && uiState == EvaViewModel.UiState.IDLE) {
            hasStartedVoice = true
            viewModel.startRecording()
        }
    }

    NavHost(
        navController = navController,
        startDestination = "home"
    ) {
        composable("home") {
            HomeScreen(
                uiState = uiState,
                messages = messages,
                isConnected = isConnected,
                onStartRecording = { viewModel.startRecording() },
                onStopRecording = { viewModel.stopRecording() },
                onStopPlayback = { viewModel.stopPlayback() },
                onSendText = { viewModel.sendTextMessage(it) },
                onSettingsClick = { navController.navigate("settings") },
                onClearError = { viewModel.clearError() },
                onClearMessages = { viewModel.clearMessages() }
            )
        }

        composable("settings") {
            SettingsScreen(
                serverUrl = serverUrl,
                userId = userId,
                isConnected = isConnected,
                onServerUrlChange = { viewModel.updateServerUrl(it) },
                onUserIdChange = { viewModel.updateUserId(it) },
                onCheckConnection = { viewModel.checkConnection() },
                onBackClick = { navController.popBackStack() }
            )
        }
    }
}
