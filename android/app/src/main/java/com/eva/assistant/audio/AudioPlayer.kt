package com.eva.assistant.audio

import android.content.Context
import android.util.Log
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

class AudioPlayer(context: Context) {

    private val player: ExoPlayer = ExoPlayer.Builder(context).build()

    private val _isPlaying = MutableStateFlow(false)
    val isPlaying: StateFlow<Boolean> = _isPlaying

    init {
        player.addListener(object : Player.Listener {
            override fun onPlaybackStateChanged(playbackState: Int) {
                when (playbackState) {
                    Player.STATE_ENDED -> {
                        _isPlaying.value = false
                    }
                    Player.STATE_READY -> {
                        if (player.playWhenReady) {
                            _isPlaying.value = true
                        }
                    }
                    Player.STATE_IDLE -> {
                        _isPlaying.value = false
                    }
                }
            }

            override fun onIsPlayingChanged(isPlaying: Boolean) {
                _isPlaying.value = isPlaying
            }
        })
    }

    fun play(url: String) {
        try {
            Log.d("AudioPlayer", "Playing: $url")
            player.stop()
            player.clearMediaItems()

            val mediaItem = MediaItem.fromUri(url)
            player.setMediaItem(mediaItem)
            player.prepare()
            player.playWhenReady = true
        } catch (e: Exception) {
            Log.e("AudioPlayer", "Failed to play audio", e)
            _isPlaying.value = false
        }
    }

    fun stop() {
        player.stop()
        _isPlaying.value = false
    }

    fun release() {
        player.release()
    }
}
