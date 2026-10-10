package com.asianagni.ramai

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.asianagni.ramai.databinding.ActivityLoginBinding
import org.json.JSONObject

class LoginActivity : AppCompatActivity() {
    private lateinit var binding: ActivityLoginBinding
    private lateinit var session: SessionStore

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionStore(this)

        if (!session.token.isNullOrBlank()) {
            startActivity(Intent(this, MainActivity::class.java))
            finish()
            return
        }

        checkBackend()
        binding.loginButton.setOnClickListener { authenticate(false) }
        binding.registerButton.setOnClickListener { authenticate(true) }
    }

    private fun checkBackend() {
        Thread {
            val result = runCatching { ApiClient.get("/health") }.getOrNull()
            runOnUiThread {
                binding.statusText.text = if (result?.ok == true) "Backend connected" else "Backend not reachable: ${BuildConfig.API_BASE_URL}"
            }
        }.start()
    }

    private fun authenticate(register: Boolean) {
        val email = binding.emailInput.text?.toString()?.trim().orEmpty()
        val password = binding.passwordInput.text?.toString().orEmpty()
        if (email.isBlank() || password.length < 8) {
            binding.statusText.text = "Enter a valid email and password (8+ characters)."
            return
        }
        binding.statusText.text = "Connecting..."
        val path = if (register) "/v1/auth/register" else "/v1/auth/login"
        Thread {
            val result = runCatching {
                ApiClient.postJson(path, JSONObject().put("email", email).put("password", password))
            }.getOrElse { ApiClient.Result(false, 0, it.message ?: "Network error") }
            runOnUiThread {
                if (result.ok) {
                    val token = runCatching { JSONObject(result.body).getString("access_token") }.getOrNull()
                    if (token != null) {
                        session.token = token
                        startActivity(Intent(this, MainActivity::class.java))
                        finish()
                    } else binding.statusText.text = "Invalid server response."
                } else {
                    binding.statusText.text = "Request failed (${result.code}): ${result.body.take(220)}"
                }
            }
        }.start()
    }
}
