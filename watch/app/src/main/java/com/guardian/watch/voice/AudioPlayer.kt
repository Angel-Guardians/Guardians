package com.guardian.watch.voice

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack

/**
 * Streams the backend's spoken reply (raw 16-bit mono PCM) to the watch speaker.
 *
 * Created per reply because the sample rate is announced in the `tts_begin`
 * control frame (24 kHz for OpenAI TTS today, but kept dynamic). Write PCM as it
 * arrives off the socket; [stop] drains and releases.
 */
class AudioPlayer(private val sampleRate: Int) {

    private var track: AudioTrack? = null

    fun start() {
        val minBytes = AudioTrack.getMinBufferSize(
            sampleRate,
            AudioFormat.CHANNEL_OUT_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
        )
        val t = AudioTrack.Builder()
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ASSISTANT)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build(),
            )
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
        t.play()
        track = t
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
    }
}
