package com.guardian.watch.voice

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioTrack
import android.util.Log

/**
 * Streams the backend's spoken reply (raw 16-bit mono PCM) to the watch speaker.
 *
 * Created per reply because the sample rate is announced in the `tts_begin`
 * control frame (24 kHz). To be reliably audible on a watch we: request audio
 * focus, bump the media stream volume, route as MEDIA/speech, and max the track
 * volume. Write PCM as it arrives off the socket; [stop] drains and releases.
 */
class AudioPlayer(context: Context, private val sampleRate: Int) {

    private val audioManager =
        context.applicationContext.getSystemService(Context.AUDIO_SERVICE) as AudioManager

    private val attributes = AudioAttributes.Builder()
        .setUsage(AudioAttributes.USAGE_MEDIA)
        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
        .build()

    private var track: AudioTrack? = null
    private var focusRequest: AudioFocusRequest? = null

    fun start() {
        // 1) Make sure the watch isn't muted — raise media volume near max.
        runCatching {
            val max = audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
            val target = maxOf(1, (max * 0.9f).toInt())
            if (audioManager.getStreamVolume(AudioManager.STREAM_MUSIC) < target) {
                audioManager.setStreamVolume(AudioManager.STREAM_MUSIC, target, 0)
            }
        }.onFailure { Log.w(TAG, "could not raise volume", it) }

        // 2) Take audio focus so the system routes + unducks our playback.
        runCatching {
            val req = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)
                .setAudioAttributes(attributes)
                .build()
            audioManager.requestAudioFocus(req)
            focusRequest = req
        }.onFailure { Log.w(TAG, "audio focus failed", it) }

        val minBytes = AudioTrack.getMinBufferSize(
            sampleRate,
            AudioFormat.CHANNEL_OUT_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
        )
        val t = AudioTrack.Builder()
            .setAudioAttributes(attributes)
            .setAudioFormat(
                AudioFormat.Builder()
                    .setSampleRate(sampleRate)
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                    .build(),
            )
            .setBufferSizeInBytes(maxOf(minBytes * 2, minBytes))
            .setTransferMode(AudioTrack.MODE_STREAM)
            .build()
        runCatching { t.setVolume(AudioTrack.getMaxVolume()) }
        t.play()
        track = t
        Log.i(TAG, "AudioTrack playing @ ${sampleRate}Hz (minBuf=$minBytes)")
    }

    /** Blocking write — back-pressures the socket reader naturally. */
    fun write(bytes: ByteArray, length: Int) {
        track?.write(bytes, 0, length, AudioTrack.WRITE_BLOCKING)
    }

    fun stop() {
        track?.let { t ->
            runCatching { t.stop() }
            t.release()
        }
        track = null
        focusRequest?.let { req ->
            runCatching { audioManager.abandonAudioFocusRequest(req) }
        }
        focusRequest = null
    }

    private companion object {
        const val TAG = "GuardianVoice"
    }
}
