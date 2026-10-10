package com.asianagni.ramai

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.speech.RecognizerIntent
import android.speech.tts.TextToSpeech
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.asianagni.ramai.databinding.ActivityMainBinding
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import org.json.JSONObject
import java.util.Locale

class MainActivity : AppCompatActivity(), TextToSpeech.OnInitListener {
    private lateinit var binding: ActivityMainBinding
    private lateinit var session: SessionStore
    private lateinit var tts: TextToSpeech

    private val speechLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val spoken = result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull()
        if (!spoken.isNullOrBlank()) {
            binding.chatInput.setText(spoken)
            sendChat(spoken)
        }
    }

    private val micPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) launchSpeech() else binding.chatResult.text = "Microphone permission is required for voice input."
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionStore(this)
        tts = TextToSpeech(this, this)

        fun open(feature: String) {
            startActivity(Intent(this, FeatureActivity::class.java).putExtra("feature", feature))
        }

        binding.mriButton.setOnClickListener { open("mri") }
        binding.ctButton.setOnClickListener { open("ct") }
        binding.audioButton.setOnClickListener { open("audio") }
        binding.cctvButton.setOnClickListener { open("cctv") }
        binding.cyberButton.setOnClickListener { open("cyber") }
        binding.glassesButton.setOnClickListener { open("smart_glasses") }

        binding.sendButton.setOnClickListener {
            val text = binding.chatInput.text?.toString()?.trim().orEmpty()
            if (text.isNotBlank()) sendChat(text)
        }
        binding.micButton.setOnClickListener { ensureMicAndSpeak() }
        binding.deleteAccountButton.setOnClickListener { confirmDeleteAccount() }
        binding.logoutButton.setOnClickListener {
            session.clear()
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
        }
    }

    private fun confirmDeleteAccount() {
        MaterialAlertDialogBuilder(this)
            .setTitle("Delete RAM AI account?")
            .setMessage("This permanently deletes the account stored by the RAM AI backend. This action cannot be undone.")
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Delete") { _, _ ->
                Thread {
                    val result = runCatching { ApiClient.delete("/v1/account", session.token) }
                        .getOrElse { ApiClient.Result(false, 0, it.message ?: "Network error") }
                    runOnUiThread {
                        if (result.ok) {
                            session.clear()
                            startActivity(Intent(this, LoginActivity::class.java))
                            finish()
                        } else {
                            binding.chatResult.text = "Account deletion failed (${result.code}): ${result.body.take(400)}"
                        }
                    }
                }.start()
            }
            .show()
    }

    private fun sendChat(text: String) {
        binding.chatResult.text = "Thinking..."
        Thread {
            val result = runCatching {
                ApiClient.postJson("/v1/chat", JSONObject().put("message", text), session.token)
            }.getOrElse { ApiClient.Result(false, 0, it.message ?: "Network error") }
            runOnUiThread {
                if (result.ok) {
                    val answer = runCatching { JSONObject(result.body).optString("answer", result.body) }.getOrElse { result.body }
                    binding.chatResult.text = answer
                    if (::tts.isInitialized) tts.speak(answer, TextToSpeech.QUEUE_FLUSH, null, "ram-ai-answer")
                } else {
                    binding.chatResult.text = "RAM AI error (${result.code}): ${result.body.take(500)}"
                }
            }
        }.start()
    }

    private fun ensureMicAndSpeak() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            launchSpeech()
        } else micPermission.launch(Manifest.permission.RECORD_AUDIO)
    }

    private fun launchSpeech() {
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
            putExtra(RecognizerIntent.EXTRA_PROMPT, "Speak to RAM AI")
        }
        runCatching { speechLauncher.launch(intent) }
            .onFailure { binding.chatResult.text = "Speech recognition is not available on this device." }
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) tts.language = Locale.getDefault()
    }

    override fun onDestroy() {
        tts.stop()
        tts.shutdown()
        super.onDestroy()
    }
}
