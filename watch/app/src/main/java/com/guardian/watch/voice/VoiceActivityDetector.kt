package com.guardian.watch.voice

/**
 * Lightweight, dependency-free voice activity detector.
 *
 * Energy (RMS) based with three robustness tricks:
 *   - an **adaptive noise floor** (slow EMA of the background level while silent),
 *     so it self-calibrates to a quiet room or a noisy one;
 *   - **hysteresis** — a higher threshold to *enter* speech than to *stay* in it,
 *     so a single dip mid-word doesn't end the utterance;
 *   - **hangover** — speech only ends after a sustained run of silent frames,
 *     and only starts after a short run of loud ones, rejecting clicks/coughs.
 *
 * Frames are fixed-size (see [AudioRecorder]); thresholds are expressed in frame
 * counts. This is the on-device gate so the watch streams *only* while the wearer
 * is actually talking. A WebRTC/Silero VAD could drop in behind the same
 * `process(rms) -> Event` shape later for noisier environments.
 */
class VoiceActivityDetector(
    private val startMultiplier: Double = 2.2,
    private val endMultiplier: Double = 1.4,
    private val absoluteFloor: Double = 130.0,
    private val minStartFrames: Int = 3,   // ~120 ms at 40 ms/frame
    private val hangoverFrames: Int = 18,  // ~720 ms of silence ends the utterance
) {
    enum class Event { NONE, START, END }

    private var inSpeech = false
    private var voicedRun = 0
    private var silenceRun = 0
    private var noiseFloor = 200.0

    fun reset() {
        inSpeech = false
        voicedRun = 0
        silenceRun = 0
        // Keep the learned noiseFloor — the room hasn't changed between utterances.
    }

    /** Feed one frame's RMS amplitude (0..32768). Returns a state transition. */
    fun process(rms: Double): Event {
        if (!inSpeech) {
            // Learn the ambient level only while we believe it's silence.
            noiseFloor += NOISE_EMA * (rms - noiseFloor)
            if (noiseFloor < 1.0) noiseFloor = 1.0
        }

        val enter = maxOf(absoluteFloor, noiseFloor * startMultiplier)
        val exit = maxOf(absoluteFloor * 0.7, noiseFloor * endMultiplier)

        if (!inSpeech) {
            if (rms > enter) {
                if (++voicedRun >= minStartFrames) {
                    inSpeech = true
                    voicedRun = 0
                    silenceRun = 0
                    return Event.START
                }
            } else {
                voicedRun = 0
            }
            return Event.NONE
        }

        // In speech: count trailing silence; end after the hangover.
        if (rms < exit) {
            if (++silenceRun >= hangoverFrames) {
                inSpeech = false
                silenceRun = 0
                return Event.END
            }
        } else {
            silenceRun = 0
        }
        return Event.NONE
    }

    private companion object {
        const val NOISE_EMA = 0.05
    }
}
