package com.example.fitnesscoachai.ui.camera

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.example.fitnesscoachai.R
import androidx.camera.view.PreviewView
import com.example.fitnesscoachai.ui.camera.CameraViewModel.AnalysisState
import kotlinx.coroutines.launch
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class CameraActivity : AppCompatActivity() {

    private lateinit var cameraExecutor: ExecutorService
    private lateinit var previewView: PreviewView
    private lateinit var tvStatus: TextView
    private lateinit var tvReps: TextView
    private lateinit var tvFeedback: TextView
    private lateinit var btnConnect: Button
    private lateinit var btnTest: Button

    private val viewModel: CameraViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_camera)

        previewView = findViewById(R.id.previewView)
        tvStatus = findViewById(R.id.tvStatus)
        tvReps = findViewById(R.id.tvReps)
        tvFeedback = findViewById(R.id.tvFeedback)
        btnConnect = findViewById(R.id.btnConnect)
        btnTest = findViewById(R.id.btnTest)

        // Наблюдаем за состоянием WebSocket
        observeViewModel()

        btnConnect.setOnClickListener {
            viewModel.connectWebSocket()
        }

        btnTest.setOnClickListener {
            // Тестовая отправка кадра
            val testBitmap = Bitmap.createBitmap(100, 100, Bitmap.Config.ARGB_8888)
            viewModel.sendFrame(testBitmap)
        }

        if (allPermissionsGranted()) {
            startCamera()
        } else {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.CAMERA),
                10
            )
        }

        cameraExecutor = Executors.newSingleThreadExecutor()

        // Авто-коннект при открытии
        viewModel.connectWebSocket()
    }

    private fun observeViewModel() {
        lifecycleScope.launch {
            viewModel.analysisState.collect { state ->
                when (state) {
                    is CameraViewModel.AnalysisState.Idle -> {
                        tvStatus.text = "Status: Idle"
                        tvFeedback.text = "Press Connect"
                    }
                    is CameraViewModel.AnalysisState.Connecting -> {
                        tvStatus.text = "Status: Connecting..."
                        tvFeedback.text = "Connecting to server..."
                    }
                    is CameraViewModel.AnalysisState.Connected -> {
                        tvStatus.text = "Status: Connected"
                        tvFeedback.text = "WebSocket connected!"
                        Toast.makeText(this@CameraActivity, "Connected!", Toast.LENGTH_SHORT).show()
                    }
                    is CameraViewModel.AnalysisState.FrameSent -> {
                        tvFeedback.text = "Frame sent to server"
                    }
                    is CameraViewModel.AnalysisState.AnalysisReceived -> {
                        val result = state.result
                        tvStatus.text = "Exercise: ${result.exercise}"
                        tvReps.text = "Reps: ${result.count}"
                        tvFeedback.text = "Feedback: ${result.feedback}"
                        if (result.errors.isNotEmpty()) {
                            tvFeedback.text = "Errors: ${result.errors.joinToString(", ")}"
                        }
                    }
                    is CameraViewModel.AnalysisState.Error -> {
                        tvStatus.text = "Status: Error"
                        tvFeedback.text = state.message
                        Toast.makeText(this@CameraActivity, state.message, Toast.LENGTH_LONG).show()
                    }
                    is CameraViewModel.AnalysisState.Disconnected -> {
                        tvStatus.text = "Status: Disconnected"
                        tvFeedback.text = "Disconnected from server"
                    }
                }
            }
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 10 && allPermissionsGranted()) {
            startCamera()
        }
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)

        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(previewView.surfaceProvider)
            }

            // Image Analysis для захвата кадров
            val imageAnalysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also {
                    it.setAnalyzer(cameraExecutor) { imageProxy ->
                        // Здесь можно захватывать кадры и отправлять на сервер
                        // Пока пропускаем
                        imageProxy.close()
                    }
                }

            val cameraSelector = CameraSelector.DEFAULT_FRONT_CAMERA

            cameraProvider.unbindAll()
            cameraProvider.bindToLifecycle(
                this,
                cameraSelector,
                preview,
                imageAnalysis
            )

        }, ContextCompat.getMainExecutor(this))
    }

    private fun allPermissionsGranted() =
        ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
        viewModel.disconnectWebSocket()
    }
}