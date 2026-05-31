package com.guardian.watch.voice

import android.util.Log
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import okio.ByteString.Companion.toByteString
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * Thin OkHttp WebSocket wrapper for the `/voice/ws` protocol (see
 * backend/api/voice.py). Control messages are JSON text frames; audio is binary.
 *
 * Uses a dedicated OkHttpClient — the REST client in
 * [com.guardian.watch.data.remote.ApiFactory] has short read/write timeouts that
 * would kill a long-lived socket. Here we disable the read timeout and rely on
 * pings to keep the connection alive.
 */
class VoiceStreamClient(private val listener: Listener) {

    /** Callbacks delivered on OkHttp's WebSocket thread — hop to your own scope. */
    interface Listener {
        fun onOpen()
        fun onTranscript(text: String)
        fun onReply(text: String, route: String)
        fun onTtsBegin(sampleRate: Int)
        fun onAudio(pcm: ByteArray)
        fun onTtsEnd()
        fun onError(message: String)
        fun onClosed()
    }

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.MILLISECONDS) // long-lived; no idle read timeout
        .pingInterval(20, TimeUnit.SECONDS)
        .build()

    @Volatile
    private var webSocket: WebSocket? = null

    val isConnected: Boolean get() = webSocket != null

    /** Open the socket. [baseUrl] is the same http(s) base the REST API uses. */
    fun connect(baseUrl: String) {
        if (webSocket != null) return
        val wsUrl = toWebSocketUrl(baseUrl)
        Log.i(TAG, "connect -> $wsUrl (from baseUrl=$baseUrl)")
        val request = Request.Builder().url(wsUrl).build()
        webSocket = client.newWebSocket(request, socketListener)
    }

    /** Begin an utterance: tell the server the format, then stream PCM via [sendAudio]. */
    fun sendStart(patientId: Int, sampleRate: Int) {
        val msg = JSONObject()
            .put("type", "start")
            .put("patient_id", patientId)
            .put("sample_rate", sampleRate)
        val ok = webSocket?.send(msg.toString())
        Log.i(TAG, "sendStart enqueued=$ok")
    }

    fun sendAudio(pcm: ByteArray, length: Int) {
        webSocket?.send(pcm.toByteString(0, length))
    }

    /** End the utterance; the server replies with transcript/reply/tts frames. */
    fun sendEnd() {
        val ok = webSocket?.send(JSONObject().put("type", "end").toString())
        Log.i(TAG, "sendEnd enqueued=$ok")
    }

    /** Ask the server to start a fall check-in (it speaks "are you okay?"). */
    fun sendFallCheckIn(patientId: Int) {
        val msg = JSONObject().put("type", "fall_checkin").put("patient_id", patientId)
        val ok = webSocket?.send(msg.toString())
        Log.i(TAG, "sendFallCheckIn enqueued=$ok")
    }

    fun close() {
        webSocket?.close(1000, null)
        webSocket = null
    }

    private val socketListener = object : WebSocketListener() {
        override fun onOpen(ws: WebSocket, response: Response) {
            Log.i(TAG, "onOpen: ${response.code} ${response.message}")
            listener.onOpen()
        }

        override fun onMessage(ws: WebSocket, text: String) {
            Log.i(TAG, "onMessage(text): $text")
            val json = runCatching { JSONObject(text) }.getOrNull() ?: return
            when (json.optString("type")) {
                "transcript" -> listener.onTranscript(json.optString("text"))
                "reply" -> listener.onReply(json.optString("text"), json.optString("route"))
                "tts_begin" -> listener.onTtsBegin(json.optInt("sample_rate", 24_000))
                "tts_end" -> listener.onTtsEnd()
                "error" -> listener.onError(json.optString("message", "voice error"))
            }
        }

        override fun onMessage(ws: WebSocket, bytes: ByteString) {
            listener.onAudio(bytes.toByteArray())
        }

        override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
            Log.w(TAG, "onFailure: code=${response?.code} msg=${t.message}", t)
            webSocket = null
            listener.onError(t.message ?: "connection failed")
        }

        override fun onClosing(ws: WebSocket, code: Int, reason: String) {
            Log.i(TAG, "onClosing: $code $reason")
        }

        override fun onClosed(ws: WebSocket, code: Int, reason: String) {
            Log.i(TAG, "onClosed: $code $reason")
            webSocket = null
            listener.onClosed()
        }
    }

    private fun toWebSocketUrl(baseUrl: String): String {
        val normalized = baseUrl.trim().trimEnd('/')
        val scheme = when {
            normalized.startsWith("https://") -> "wss://" + normalized.removePrefix("https://")
            normalized.startsWith("http://") -> "ws://" + normalized.removePrefix("http://")
            else -> "ws://$normalized"
        }
        return "$scheme/voice/ws"
    }

    private companion object {
        const val TAG = "GuardianVoice"
    }
}
