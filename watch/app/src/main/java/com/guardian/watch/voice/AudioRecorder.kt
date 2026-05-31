package com.guardian.watch.voice

import android.Manifest
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import androidx.annotation.RequiresPermission

/**
 * Captures microphone audio as raw 16-bit mono PCM at 16 kHz — the format the
 * backend's Whisper STT expects — and hands each chunk to a callback as it's read.
 *
 * Deliberately dumb: no encoding, no VAD. The backend decides when speech ends;
 * the watch just streams between push-to-talk press and release.
 */
class AudioRecorder {

    @Volatile
    private var record: AudioRecord? = null

    @Volatile
    private var running = false

    /**
     * Arm the recorder. Call this *before* launching [record] so a fast
     * press-then-release can't lose the race and leave [record] looping forever.
     */
    fun start() {
        running = true
    }

    /**
     * Capture on the calling thread and block, invoking [onChunk] for each PCM
     * buffer until [stop] is called (or if [stop] already ran, return at once).
     * Run this on a background dispatcher, after [start].
     */
    @RequiresPermission(Manifest.permission.RECORD_AUDIO)
    fun record(onChunk: (ByteArray, Int) -> Unit) {
        if (!running) return
        val minBytes = AudioRecord.getMinBufferSize(
            SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
        )
        if (minBytes <= 0) return
        // A roomy buffer (4x min) keeps us from dropping frames if the network
        // send momentarily stalls; we read ~40 ms at a time.
        val bufferBytes = maxOf(minBytes * 4, CHUNK_BYTES * 4)

        val rec = AudioRecord(
            MediaRecorder.AudioSource.VOICE_RECOGNITION,
            SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            bufferBytes,
        )
        if (rec.state != AudioRecord.STATE_INITIALIZED) {
            rec.release()
            return
        }

        record = rec
        val buffer = ByteArray(CHUNK_BYTES)
        try {
            rec.startRecording()
            while (running) {
                val read = rec.read(buffer, 0, buffer.size)
                if (read > 0) onChunk(buffer, read)
            }
        } finally {
            runCatching { rec.stop() }
            rec.release()
            record = null
        }
    }

    fun stop() {
        running = false
    }

    companion object {
        const val SAMPLE_RATE = 16_000

        // 40 ms @ 16 kHz, 16-bit mono = 16000 * 0.04 * 2 bytes.
        private const val CHUNK_BYTES = 1_280
    }
}
