package com.example.fitnesscoachai.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.fitnesscoachai.data.api.RetrofitClient
import com.example.fitnesscoachai.data.models.LoginRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class AuthViewModel : ViewModel() {

    private val _loginState = MutableStateFlow<LoginState>(LoginState.Idle)
    val loginState: StateFlow<LoginState> = _loginState

    fun login(email: String, password: String) {
        viewModelScope.launch {
            _loginState.value = LoginState.Loading
            try {
                val response = RetrofitClient.apiService.login(
                    LoginRequest(email, password)
                )

                if (response.isSuccessful && response.body() != null) {
                    val authResponse = response.body()!!
                    // TODO: сохранить токен в DataStore
                    _loginState.value = LoginState.Success(authResponse)
                } else {
                    _loginState.value = LoginState.Error(
                        "Login failed: ${response.code()} - ${response.message()}"
                    )
                }
            } catch (e: Exception) {
                _loginState.value = LoginState.Error("Network error: ${e.message}")
            }
        }
    }

    sealed class LoginState {
        object Idle : LoginState()
        object Loading : LoginState()
        data class Success(val authResponse: com.example.fitnesscoachai.data.models.AuthResponse) : LoginState()
        data class Error(val message: String) : LoginState()
    }
}