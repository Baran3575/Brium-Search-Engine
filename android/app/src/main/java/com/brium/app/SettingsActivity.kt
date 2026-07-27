package com.brium.app

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.appbar.MaterialToolbar

class SettingsActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)

        val toolbar = findViewById<MaterialToolbar>(R.id.toolbar)
        setSupportActionBar(toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.setDisplayShowHomeEnabled(true)
        toolbar.setNavigationOnClickListener { finish() }

        val prefs = getSharedPreferences("brium", MODE_PRIVATE)
        val currentUrl = prefs.getString("server_url", "") ?: ""

        val input = findViewById<com.google.android.material.textfield.TextInputEditText>(R.id.serverUrlInput)
        input.setText(currentUrl)

        findViewById<com.google.android.material.button.MaterialButton>(R.id.saveButton).setOnClickListener {
            val url = input.text.toString().trim()
            if (url.isBlank()) {
                input.error = "Enter a server URL"
                return@setOnClickListener
            }
            val normalized = if (url.startsWith("http")) url else "http://$url"
            prefs.edit().putString("server_url", normalized).apply()
            setResult(RESULT_OK, Intent().putExtra("server_url", normalized))
            finish()
        }
    }
}
