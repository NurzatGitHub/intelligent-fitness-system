package com.example.fitnesscoachai.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.fitnesscoachai.data.api.RetrofitClient
import com.example.fitnesscoachai.data.models.LoginRequest
import com.example.fitnesscoachai.data.models.SignupRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class AuthViewModel : ViewModel() {

    private val _loginState = MutableStateFlow<LoginState>(LoginState.Idle)
    val loginState: StateFlow<LoginState> = _loginState

    private val _signupState = MutableStateFlow<SignupState>(SignupState.Idle)
    val signupState: StateFlow<SignupState> = _signupState

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

    fun signup(email: String, username: String, password: String) {
        viewModelScope.launch {
            _signupState.value = SignupState.Loading
            try {
                val response = RetrofitClient.apiService.signup(
                    SignupRequest(email, username, password)
                )

                if (response.isSuccessful && response.body() != null) {
                    val authResponse = response.body()!!
                    _signupState.value = SignupState.Success(authResponse)
                } else {
                    _signupState.value = SignupState.Error(
                        "Signup failed: ${response.code()} - ${response.message()}"
                    )
                }
            } catch (e: Exception) {
                _signupState.value = SignupState.Error("Network error: ${e.message}")
            }
        }
    }

    sealed class LoginState {
        object Idle : LoginState()
        object Loading : LoginState()
        data class Success(val authResponse: com.example.fitnesscoachai.data.models.AuthResponse) : LoginState()
        data class Error(val message: String) : LoginState()
    }

    sealed class SignupState {
        object Idle : SignupState()
        object Loading : SignupState()
        data class Success(val authResponse: com.example.fitnesscoachai.data.models.AuthResponse) : SignupState()
        data class Error(val message: String) : SignupState()
    }
}