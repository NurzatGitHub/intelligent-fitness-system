package com.example.fitnesscoachai.data.models

data class User(
    val id: Int,
    val email: String,
    val username: String,
    val age: Int? = null,
    val weight: Float? = null,
    val height: Float? = null,
    val fitness_level: String = "beginner"
)

data class LoginRequest(
    val email: String,
    val password: String
)

data class AuthResponse(
    val user: User,
    val refresh: String,
    val access: String
)