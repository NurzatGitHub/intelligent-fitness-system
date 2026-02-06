package com.example.fitnesscoachai.ui.auth

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.fitnesscoachai.MainActivity
import com.example.fitnesscoachai.R
import kotlinx.coroutines.launch

class SignupActivity : AppCompatActivity() {

    private lateinit var etEmail: EditText
    private lateinit var etUsername: EditText
    private lateinit var etPassword: EditText
    private lateinit var etConfirmPassword: EditText
    private lateinit var btnSignup: Button
    private lateinit var tvLoginLink: TextView

    private val viewModel: AuthViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_signup)

        etEmail = findViewById(R.id.etEmail)
        etUsername = findViewById(R.id.etUsername)
        etPassword = findViewById(R.id.etPassword)
        etConfirmPassword = findViewById(R.id.etConfirmPassword)
        btnSignup = findViewById(R.id.btnSignup)
        tvLoginLink = findViewById(R.id.tvLoginLink)

        setupObservers()

        btnSignup.setOnClickListener {
            signup()
        }

        tvLoginLink.setOnClickListener {
            startActivity(Intent(this, AuthActivity::class.java))
            finish()
        }
    }

    private fun setupObservers() {
        lifecycleScope.launch {
            viewModel.signupState.collect { state ->
                Log.d("SignupActivity", "Signup state: $state")

                when (state) {
                    is AuthViewModel.SignupState.Idle -> {
                        Log.d("SignupActivity", "State: Idle")
                    }
                    is AuthViewModel.SignupState.Loading -> {
                        Log.d("SignupActivity", "State: Loading")
                        btnSignup.isEnabled = false
                        btnSignup.text = "Loading..."
                    }
                    is AuthViewModel.SignupState.Success -> {
                        Log.d("SignupActivity", "State: Success - ${state.authResponse.access.take(20)}...")
                        btnSignup.isEnabled = true
                        btnSignup.text = "Sign Up"

                        // Сохраняем токен
                        saveAuthData(state.authResponse)

                        // Переходим на главный экран
                        startActivity(Intent(this@SignupActivity, MainActivity::class.java))
                        finish()
                    }
                    is AuthViewModel.SignupState.Error -> {
                        Log.e("SignupActivity", "State: Error - ${state.message}")
                        btnSignup.isEnabled = true
                        btnSignup.text = "Sign Up"
                        Toast.makeText(
                            this@SignupActivity,
                            "Error: ${state.message}",
                            Toast.LENGTH_LONG
                        ).show()
                    }
                }
            }
        }
    }

    private fun signup() {
        val email = etEmail.text.toString().trim()
        val username = etUsername.text.toString().trim()
        val password = etPassword.text.toString().trim()
        val confirmPassword = etConfirmPassword.text.toString().trim()

        if (email.isEmpty() || username.isEmpty() || password.isEmpty() || confirmPassword.isEmpty()) {
            Toast.makeText(this, "Please fill all fields", Toast.LENGTH_SHORT).show()
            return
        }

        if (password != confirmPassword) {
            Toast.makeText(this, "Passwords do not match", Toast.LENGTH_SHORT).show()
            return
        }

        if (password.length < 6) {
            Toast.makeText(this, "Password must be at least 6 characters", Toast.LENGTH_SHORT).show()
            return
        }

        viewModel.signup(email, username, password)
    }

    private fun saveAuthData(authResponse: com.example.fitnesscoachai.data.models.AuthResponse) {
        // Используем commit() для гарантированного сохранения
        getSharedPreferences("auth", MODE_PRIVATE).edit()
            .putString("access_token", authResponse.access)
            .putString("refresh_token", authResponse.refresh)
            .putBoolean("isLoggedIn", true)
            .commit() // commit() гарантирует синхронное сохранение
    }
}
