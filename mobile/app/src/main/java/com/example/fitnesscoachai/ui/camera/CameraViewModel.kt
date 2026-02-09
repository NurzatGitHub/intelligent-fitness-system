package com.example.fitnesscoachai.ui.camera

import android.graphics.Bitmap
import android.util.Base64
import androidx.lifecycle.ViewModel
import com.google.gson.Gson
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import okhttp3.*
import org.json.JSONObject
import java.io.ByteArrayOutputStream

// Модель для результата анализа
data class AnalysisResult(
    val exercise: String,
    val count: Int,
    val errors: List<String>,
    val feedback: String,
    val score: Int
)

class CameraViewModel : ViewModel() {

    private val webSocketClient: OkHttpClient = OkHttpClient.Builder().build()
    private var webSocket: WebSocket? = null

    private val _analysisState = MutableStateFlow<AnalysisState>(AnalysisState.Idle)
    val analysisState: StateFlow<AnalysisState> = _analysisState

    fun connectWebSocket() {
        val request = Request.Builder()
            .url("ws://10.0.2.2:8000/ws/analyze/")  // Для эмулятора
            // .url("ws://192.168.0.12:8000/ws/analyze/")  // Для реального устройства
            .build()

        webSocket = webSocketClient.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                _analysisState.value = AnalysisState.Connected
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                try {
                    val analysis = Gson().fromJson(text, AnalysisResult::class.java)
                    _analysisState.value = AnalysisState.AnalysisReceived(analysis)
                } catch (e: Exception) {
                    _analysisState.value = AnalysisState.Error("Failed to parse analysis")
                }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                _analysisState.value = AnalysisState.Error("WebSocket failed: ${t.message}")
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                _analysisState.value = AnalysisState.Disconnected
            }
        })
    }

    fun sendFrame(bitmap: Bitmap) {
        try {
            // Конвертируем в base64
            val byteArrayOutputStream = ByteArrayOutputStream()
            bitmap.compress(Bitmap.CompressFormat.JPEG, 70, byteArrayOutputStream)
            val base64Image = Base64.encodeToString(
                byteArrayOutputStream.toByteArray(),
                Base64.DEFAULT
            )

            // Отправляем через WebSocket
            val frameData = JSONObject().apply {
                put("type", "frame")
                put("frame", base64Image)
            }.toString()

            webSocket?.send(frameData)
            _analysisState.value = AnalysisState.FrameSent

        } catch (e: Exception) {
            _analysisState.value = AnalysisState.Error("Failed to send frame: ${e.message}")
        }
    }

    fun disconnectWebSocket() {
        webSocket?.close(1000, "Normal closure")
        webSocket = null
        _analysisState.value = AnalysisState.Disconnected
    }

    sealed class AnalysisState {
        object Idle : AnalysisState()
        object Connecting : AnalysisState()
        object Connected : AnalysisState()
        object FrameSent : AnalysisState()
        data class AnalysisReceived(val result: AnalysisResult) : AnalysisState()
        data class Error(val message: String) : AnalysisState()
        object Disconnected : AnalysisState()
    }
}