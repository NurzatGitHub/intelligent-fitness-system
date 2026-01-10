package com.example.fitnesscoachai.data.api

import com.example.fitnesscoachai.data.models.AuthResponse
import com.example.fitnesscoachai.data.models.LoginRequest
import com.example.fitnesscoachai.data.models.User
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST

interface ApiService {
    @POST("auth/login/")
    suspend fun login(@Body request: LoginRequest): Response<AuthResponse>

    @GET("auth/profile/")
    suspend fun getProfile(@Header("Authorization") token: String): Response<User>
}