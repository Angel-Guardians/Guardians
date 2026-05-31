package com.guardian.watch.voice

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import androidx.core.content.ContextCompat
import com.guardian.watch.data.settings.SettingsStore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

/**
 * Drives one push-to-talk voice turn end-to-end against `/voice/ws`:
 *
 *   press  -> open socket (if needed), `start`, stream mic PCM up
 *   release-> stop mic, `end`, wait for transcript + reply
 *   reply  -> play the streamed TTS PCM back through the speaker
 *
 * Half-duplex by construction: the mic only runs between press and release, so
 * the watch never records its own playback — no echo, no acoustic feedback, and
 * no need for echo cancellation. The socket stays open across turns; [shutdown]
 * tears everything down when the user leaves the voice screen.
 */
class VoiceSession(
    private val context: Context,
    private val settings: SettingsStore,
) : VoiceStreamClient.Listener {

    enum class Phase { Idle, Connecting, Listening, Thinking, Speaking }

    data class UiState(
        val phase: Phase = Phase.Idle,
        val transcript: String = "",
        val reply: String = "",
        val error: String? = null,
    )

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private val client = VoiceStreamClient(this)
    private val recorder = AudioRecorder()

    @Volatile
    private var player: AudioPlayer? = null

    @Volatile
    private var recordJob: Job? = null

    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state.asStateFlow()

    private fun hasMicPermission(): Boolean =
        ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) ==
            PackageManager.PERMISSION_GRANTED

    /** Push-to-talk pressed: connect if needed and start streaming the mic. */
    fun startTalking() {
        if (!hasMicPermission()) {
            _state.value = _state.value.copy(error = "Microphone permission needed")
            return
        }
        // Interrupt any reply that's still playing so the user can barge in.
        stopPlayback()

        _state.value = UiState(phase = if (client.isConnected) Phase.Listening else Phase.Connecting)

        // Arm before launching so a fast release can't lose the race (see AudioRecorder).
        recorder.start()
        recordJob = scope.launch {
            val baseUrl = settings.baseUrl.first()
            val patientId = settings.patientId.first()
            client.connect(baseUrl)
            client.sendStart(patientId, AudioRecorder.SAMPLE_RATE)
            _state.value = _state.value.copy(phase = Phase.Listening)
            launch(Dispatchers.IO) {
                runCatching {
                    recorder.record { chunk, len -> client.sendAudio(chunk, len) }
                }.onFailure { _state.value = _state.value.copy(error = it.message) }
            }
        }
    }

    /** Push-to-talk released: stop the mic and ask the backend to answer. */
    fun stopTalking() {
        recorder.stop()
        recordJob = null
        if (_state.value.phase == Phase.Listening || _state.value.phase == Phase.Connecting) {
            _state.value = _state.value.copy(phase = Phase.Thinking)
            client.sendEnd()
        }
    }

    fun shutdown() {
        recorder.stop()
        stopPlayback()
        client.close()
        scope.cancel()
    }

    private fun stopPlayback() {
        player?.stop()
        player = null
    }

    // --- VoiceStreamClient.Listener (called on OkHttp's reader thread) ---------

    override fun onOpen() { /* state already advanced by the caller */ }

    override fun onTranscript(text: String) {
        _state.value = _state.value.copy(
            transcript = text,
            // Empty transcript = silence/no speech detected; the turn is over.
            phase = if (text.isBlank()) Phase.Idle else _state.value.phase,
        )
    }

    override fun onReply(text: String, route: String) {
        _state.value = _state.value.copy(
            reply = text,
            phase = if (text.isBlank()) Phase.Idle else _state.value.phase,
        )
    }

    override fun onTtsBegin(sampleRate: Int) {
        stopPlayback()
        player = AudioPlayer(sampleRate).also { it.start() }
        _state.value = _state.value.copy(phase = Phase.Speaking)
    }

    override fun onAudio(pcm: ByteArray) {
        player?.write(pcm, pcm.size)
    }

    override fun onTtsEnd() {
        stopPlayback()
        _state.value = _state.value.copy(phase = Phase.Idle)
    }

    override fun onError(message: String) {
        recorder.stop()
        stopPlayback()
        _state.value = _state.value.copy(phase = Phase.Idle, error = message)
    }

    override fun onClosed() {
        if (_state.value.phase != Phase.Idle) {
            _state.value = _state.value.copy(phase = Phase.Idle)
        }
    }
}
