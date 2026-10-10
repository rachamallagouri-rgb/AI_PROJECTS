package com.asianagni.ramai

import android.net.Uri
import android.os.Bundle
import android.view.View
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.asianagni.ramai.databinding.ActivityFeatureBinding
import org.json.JSONArray
import org.json.JSONObject

class FeatureActivity : AppCompatActivity() {
    private lateinit var binding: ActivityFeatureBinding
    private lateinit var session: SessionStore
    private lateinit var feature: String
    private var selectedUri: Uri? = null

    private val filePicker = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        selectedUri = uri
        binding.selectedFileText.text = uri?.lastPathSegment ?: "No file selected"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityFeatureBinding.inflate(layoutInflater)
        setContentView(binding.root)
        session = SessionStore(this)
        feature = intent.getStringExtra("feature") ?: "mri"
        configureUi()

        binding.selectFileButton.setOnClickListener { filePicker.launch(arrayOf("*/*")) }
        binding.runButton.setOnClickListener { runFeature() }
    }

    private fun configureUi() {
        val (title, help) = when (feature) {
            "mri" -> "NeuroSpec MRI" to "Select a processed MRI .npz/.npy file exported for your model. The backend runs the configured MRI model."
            "ct" -> "NeuroSpec CT" to "Select CT .dcm, .npz, .npy, JPG or PNG input."
            "audio" -> "Audio AI" to "Select WAV/NPY/NPZ audio input for your trained audio model."
            "cctv" -> "CCTV AI" to "Select an image/frame to run the configured CCTV vision model."
            "cyber" -> "Cyber Defense" to "Paste a numeric feature array, for example: [0.1, 1.2, 3.4]. This module is defensive intrusion detection only."
            "smart_glasses" -> "Smart Glasses" to "Use RAM AI voice on the home screen. Hardware camera streaming can connect to the CCTV endpoint in the next hardware integration phase."
            else -> "RAM AI Feature" to "Run a configured RAM AI feature."
        }
        binding.titleText.text = title
        binding.helpText.text = help

        val textMode = feature == "cyber" || feature == "smart_glasses"
        binding.textInputLayout.visibility = if (textMode) View.VISIBLE else View.GONE
        binding.selectFileButton.visibility = if (textMode) View.GONE else View.VISIBLE
        binding.selectedFileText.visibility = if (textMode) View.GONE else View.VISIBLE
        if (feature == "smart_glasses") {
            binding.textInput.setText("Smart-glasses voice path is active through the RAM AI home voice assistant.")
        }
    }

    private fun runFeature() {
        binding.resultText.text = "Running..."
        Thread {
            val result = try {
                when (feature) {
                    "cyber" -> runCyber()
                    "smart_glasses" -> ApiClient.get("/v1/models/status", session.token)
                    else -> {
                        val uri = selectedUri ?: return@Thread runOnUiThread {
                            binding.resultText.text = "Select an input file first."
                        }
                        ApiClient.upload("/v1/$feature/analyze", uri, contentResolver, session.token)
                    }
                }
            } catch (e: Exception) {
                ApiClient.Result(false, 0, e.message ?: "Unknown error")
            }
            runOnUiThread {
                binding.resultText.text = if (result.ok) pretty(result.body) else "Error (${result.code}): ${result.body}"
            }
        }.start()
    }

    private fun runCyber(): ApiClient.Result {
        val raw = binding.textInput.text?.toString()?.trim().orEmpty()
        val arr = JSONArray(raw)
        val body = JSONObject().put("features", arr)
        return ApiClient.postJson("/v1/cyber/analyze", body, session.token)
    }

    private fun pretty(raw: String): String = runCatching {
        JSONObject(raw).toString(2)
    }.getOrElse { raw }
}
