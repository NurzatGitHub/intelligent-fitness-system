package com.example.fitnesscoachai.ui.auth

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import androidx.appcompat.app.AppCompatActivity
import com.example.fitnesscoachai.MainActivity
import com.example.fitnesscoachai.R

class AuthActivity : AppCompatActivity() {

    private lateinit var etEmail: EditText
    private lateinit var etPassword: EditText
    private lateinit var btnLogin: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_auth)

        etEmail = findViewById(R.id.etEmail)
        etPassword = findViewById(R.id.etPassword)
        btnLogin = findViewById(R.id.btnLogin)

        btnLogin.setOnClickListener {
            login()
        }
    }

    private fun login() {
        val email = etEmail.text.toString()
        val password = etPassword.text.toString()

        if (email.isNotEmpty() && password.isNotEmpty()) {
            getSharedPreferences("auth", MODE_PRIVATE)
                .edit()
                .putBoolean("isLoggedIn", true)
                .apply()

            startActivity(Intent(this, MainActivity::class.java))
            finish()
        }
    }
}

