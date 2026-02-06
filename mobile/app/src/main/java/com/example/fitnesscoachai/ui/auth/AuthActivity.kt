package com.example.fitnesscoachai.ui.auth

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.fitnesscoachai.MainActivity
import com.example.fitnesscoachai.R
import com.example.fitnesscoachai.ui.auth.SignupActivity
import kotlinx.coroutines.launch

class AuthActivity : AppCompatActivity() {

    private lateinit var etEmail: EditText
    private lateinit var etPassword: EditText
    private lateinit var btnLogin: Button
    private lateinit var tvSignupLink: android.widget.TextView

    private val viewModel: AuthViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Проверяем, авторизован ли пользователь
        val isLoggedIn = getSharedPreferences("auth", MODE_PRIVATE)
            .getBoolean("isLoggedIn", false)
        
        val accessToken = getSharedPreferences("auth", MODE_PRIVATE)
            .getString("access_token", null)

        // Если пользователь уже авторизован и есть токен, переходим на главный экран
        if (isLoggedIn && !accessToken.isNullOrEmpty()) {
            startActivity(Intent(this, MainActivity::class.java))
            finish()
            return
        }
        
        setContentView(R.layout.activity_auth)

        etEmail = findViewById(R.id.etEmail)
        etPassword = findViewById(R.id.etPassword)
        btnLogin = findViewById(R.id.btnLogin)
        tvSignupLink = findViewById(R.id.tvSignupLink)

        setupObservers()

        btnLogin.setOnClickListener {
            login()
        }

        tvSignupLink.setOnClickListener {
            startActivity(Intent(this, SignupActivity::class.java))
            finish()
        }
    }

    private fun setupObservers() {
        lifecycleScope.launch {
            viewModel.loginState.collect { state ->
                Log.d("AuthActivity", "Login state: $state")  // ДОБАВЬ ЭТУ СТРОКУ

                when (state) {
                    is AuthViewModel.LoginState.Idle -> {
                        Log.d("AuthActivity", "State: Idle")
                    }
                    is AuthViewModel.LoginState.Loading -> {
                        Log.d("AuthActivity", "State: Loading")
                        btnLogin.isEnabled = false
                        btnLogin.text = "Loading..."
                    }
                    is AuthViewModel.LoginState.Success -> {
                        Log.d("AuthActivity", "State: Success - ${state.authResponse.access.take(20)}...")
                        btnLogin.isEnabled = true
                        btnLogin.text = "Login"

                        // Сохраняем токен
                        saveAuthData(state.authResponse)

                        // Переходим на главный экран
                        startActivity(Intent(this@AuthActivity, MainActivity::class.java))
                        finish()
                    }
                    is AuthViewModel.LoginState.Error -> {
                        Log.e("AuthActivity", "State: Error - ${state.message}")
                        btnLogin.isEnabled = true
                        btnLogin.text = "Login"
                        Toast.makeText(
                            this@AuthActivity,
                            "Error: ${state.message}",
                            Toast.LENGTH_LONG
                        ).show()
                    }
                }
            }
        }
    }

    private fun login() {
        val email = etEmail.text.toString().trim()
        val password = etPassword.text.toString().trim()

        if (email.isEmpty() || password.isEmpty()) {
            Toast.makeText(this, "Please fill all fields", Toast.LENGTH_SHORT).show()
            return
        }

        viewModel.login(email, password)
    }

    private fun saveAuthData(authResponse: com.example.fitnesscoachai.data.models.AuthResponse) {
        // Временное решение - позже заменим на DataStore
        // Используем commit() для гарантированного сохранения
        getSharedPreferences("auth", MODE_PRIVATE).edit()
            .putString("access_token", authResponse.access)
            .putString("refresh_token", authResponse.refresh)
            .putBoolean("isLoggedIn", true)
            .commit() // commit() гарантирует синхронное сохранение
    }
}