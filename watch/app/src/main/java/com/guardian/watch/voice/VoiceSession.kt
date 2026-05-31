package com.guardian.watch.voice

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.util.Log
import androidx.core.content.ContextCompat
import com.guardian.watch.data.settings.SettingsStore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlin.math.min
import kotlin.math.sqrt

/**
 * Hands-free voice against `/voice/ws`, gated by on-device VAD.
 *
 * When enabled, the mic runs continuously and [VoiceActivityDetector] decides
 * when the wearer is speaking: on speech onset we open an utterance (`start` +
 * a short pre-roll so the first syllable isn't clipped) and stream PCM; on
 * sustained silence we send `end` and wait for the spoken reply.
 *
 * Half-duplex by design: while we're waiting for a reply (Thinking) or playing
 * one (Speaking) the mic frames are dropped, so the watch never re-detects its
 * own TTS as speech. After the reply finishes we re-arm and listen again. A
 * watchdog re-arms us if the backend goes quiet, so one stuck turn can't wedge
 * the session.
 */
class VoiceSession(
    private val context: Context,
    private val settings: SettingsStore,
) : VoiceStreamClient.Listener {

    enum class Phase { Off, Listening, Capturing, Thinking, Speaking }

    data class UiState(
        val phase: Phase = Phase.Off,
        val transcript: String = "",
        val reply: String = "",
        val level: Float = 0f,
        val error: String? = null,
    )

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private val client = VoiceStreamClient(this)
    private val recorder = AudioRecorder()
    private val vad = VoiceActivityDetector()

    @Volatile
    private var player: AudioPlayer? = null

    @Volatile
    private var enabled = false

    @Volatile
    private var baseUrl: String = ""

    @Volatile
    private var patientId: Int = SettingsStore.DEFAULT_PATIENT_ID

    private var loopJob: Job? = null
    private var watchdog: Job? = null

    // Recent frames kept so a detected utterance includes a little audio from
    // *before* the VAD fired (energy VAD always trips a frame or two late).
    private val preRoll = ArrayDeque<ByteArray>()

    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state.asStateFlow()

    val isEnabled: Boolean get() = enabled

    private fun hasMicPermission(): Boolean =
        ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) ==
            PackageManager.PERMISSION_GRANTED

    /** Turn hands-free voice on or off. */
    fun setEnabled(on: Boolean) {
        if (on == enabled) return
        if (on) startListening() else stopListening()
    }

    /**
     * Begin a hands-free fall check-in: ask the server to speak "are you okay?",
     * then listen for the answer (handled like any utterance, but the server
     * follows up based on it — calling for help if they're hurt). Works whether
     * or not the voice assistant was already on.
     */
    fun startFallCheckIn() {
        if (!hasMicPermission()) {
            _state.value = _state.value.copy(error = "Microphone permission needed")
            return
        }
        watchdog?.cancel()
        stopPlayback()
        if (!enabled) {
            enabled = true
            vad.reset()
            preRoll.clear()
            // Gate the mic (phase != Listening/Capturing) until the spoken
            // question finishes; then onTtsEnd re-arms us to capture the answer.
            _state.value = UiState(phase = Phase.Thinking)
            recorder.start()
            loopJob = scope.launch(Dispatchers.IO) {
                baseUrl = settings.baseUrl.first()
                patientId = settings.patientId.first()
                client.connect(baseUrl)
                client.sendFallCheckIn(patientId)
                runCatching {
                    recorder.record { chunk, len -> onFrame(chunk, len) }
                }.onFailure { Log.w(TAG, "recorder failed", it) }
            }
        } else {
            vad.reset()
            preRoll.clear()
            _state.value = _state.value.copy(phase = Phase.Thinking, level = 0f)
            scope.launch(Dispatchers.IO) {
                client.connect(baseUrl)
                client.sendFallCheckIn(patientId)
            }
        }
    }

    private fun startListening() {
        if (!hasMicPermission()) {
            _state.value = _state.value.copy(error = "Microphone permission needed")
            return
        }
        enabled = true
        vad.reset()
        preRoll.clear()
        _state.value = UiState(phase = Phase.Listening)
        recorder.start()
        loopJob = scope.launch(Dispatchers.IO) {
            baseUrl = settings.baseUrl.first()
            patientId = settings.patientId.first()
            Log.i(TAG, "voice enabled: baseUrl=$baseUrl patientId=$patientId")
            client.connect(baseUrl)
            var frames = 0
            runCatching {
                recorder.record { chunk, len ->
                    onFrame(chunk, len)
                    frames++
                }
            }.onFailure { Log.w(TAG, "recorder failed", it) }
            Log.i(TAG, "recorder stopped after $frames frames")
        }
    }

    private fun stopListening() {
        enabled = false
        recorder.stop()
        loopJob = null
        watchdog?.cancel()
        stopPlayback()
        client.close()
        _state.value = UiState(phase = Phase.Off)
    }

    /**
     * Clear the current conversation (transcript / reply / error) and start
     * fresh. If voice is on we abandon any in-flight turn and re-arm listening;
     * if it's off we just wipe the displayed state.
     */
    fun reset() {
        watchdog?.cancel()
        stopPlayback()
        if (enabled) {
            client.close() // drop any half-open turn; next speech reconnects
            vad.reset()
            preRoll.clear()
            _state.value = UiState(phase = Phase.Listening)
        } else {
            _state.value = UiState(phase = Phase.Off)
        }
    }

    fun shutdown() {
        recorder.stop()
        stopPlayback()
        client.close()
        scope.cancel()
    }

    // --- Capture loop (runs on the recorder's IO thread) ----------------------

    private fun onFrame(chunk: ByteArray, len: Int) {
        val phase = _state.value.phase
        // Half-duplex gate: never feed the mic while thinking or speaking.
        if (phase != Phase.Listening && phase != Phase.Capturing) return

        val rms = rms(chunk, len)
        if (phase == Phase.Listening) {
            preRoll.addLast(chunk.copyOf(len))
            if (preRoll.size > PRE_ROLL_FRAMES) preRoll.removeFirst()
        }

        when (vad.process(rms)) {
            VoiceActivityDetector.Event.START -> {
                client.connect(baseUrl) // reconnect if a prior turn dropped the socket
                client.sendStart(patientId, AudioRecorder.SAMPLE_RATE)
                preRoll.forEach { client.sendAudio(it, it.size) }
                preRoll.clear()
                client.sendAudio(chunk, len)
                _state.value = _state.value.copy(phase = Phase.Capturing, level = level(rms))
            }

            VoiceActivityDetector.Event.NONE -> {
                if (phase == Phase.Capturing) client.sendAudio(chunk, len)
                _state.value = _state.value.copy(level = level(rms))
            }

            VoiceActivityDetector.Event.END -> {
                client.sendAudio(chunk, len) // include the trailing frame
                client.sendEnd()
                _state.value = _state.value.copy(phase = Phase.Thinking, level = 0f)
                startWatchdog()
            }
        }
    }

    /** Re-arm for the next utterance (keeps the session and socket alive). */
    private fun reArm() {
        watchdog?.cancel()
        if (!enabled) return
        vad.reset()
        preRoll.clear()
        _state.value = _state.value.copy(phase = Phase.Listening, level = 0f)
    }

    private fun startWatchdog() {
        watchdog?.cancel()
        watchdog = scope.launch {
            delay(WATCHDOG_MS)
            if (_state.value.phase == Phase.Thinking) {
                Log.w(TAG, "watchdog: no reply, re-arming")
                _state.value = _state.value.copy(error = "No response from server")
                reArm()
            }
        }
    }

    private fun stopPlayback() {
        player?.stop()
        player = null
    }

    private fun rms(buf: ByteArray, len: Int): Double {
        if (len < 2) return 0.0
        var sum = 0.0
        var i = 0
        val n = len / 2
        while (i < len - 1) {
            val lo = buf[i].toInt() and 0xff
            val hi = buf[i + 1].toInt() // sign-extends -> signed 16-bit sample
            val s = (hi shl 8) or lo
            sum += (s * s).toDouble()
            i += 2
        }
        return sqrt(sum / n)
    }

    private fun level(rms: Double): Float = min(1.0, rms / 3000.0).toFloat()

    // --- VoiceStreamClient.Listener (called on OkHttp's reader thread) ---------

    override fun onOpen() { /* utterance state is driven by the VAD, not by open */ }

    override fun onTranscript(text: String) {
        watchdog?.cancel()
        _state.value = _state.value.copy(transcript = text)
        if (text.isBlank()) reArm() // false trigger / no speech recognised
    }

    override fun onReply(text: String, route: String) {
        _state.value = _state.value.copy(reply = text)
        if (text.isBlank()) reArm()
    }

    override fun onTtsBegin(sampleRate: Int) {
        watchdog?.cancel()
        stopPlayback()
        player = AudioPlayer(sampleRate).also { it.start() }
        _state.value = _state.value.copy(phase = Phase.Speaking, level = 0f)
    }

    override fun onAudio(pcm: ByteArray) {
        player?.write(pcm, pcm.size)
    }

    override fun onTtsEnd() {
        stopPlayback()
        reArm()
    }

    override fun onError(message: String) {
        Log.w(TAG, "onError: $message")
        stopPlayback()
        _state.value = _state.value.copy(error = message)
        reArm()
    }

    override fun onClosed() {
        // Socket dropped; the next detected utterance will reconnect.
        if (enabled && _state.value.phase != Phase.Off) reArm()
    }

    private companion object {
        const val TAG = "GuardianVoice"
        const val PRE_ROLL_FRAMES = 8 // ~320 ms of audio before the VAD fires
        const val WATCHDOG_MS = 15_000L
    }
}
