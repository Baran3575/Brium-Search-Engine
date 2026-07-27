package com.brium.app

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class SettingsActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        val prefs = getSharedPreferences("brium", MODE_PRIVATE)
        val currentUrl = prefs.getString("server_url", "http://10.0.2.2:8000") ?: "http://10.0.2.2:8000"

        findViewById<android.widget.EditText>(R.id.serverUrlInput).setText(currentUrl)

        findViewById<android.widget.Button>(R.id.saveButton).setOnClickListener {
            val url = findViewById<android.widget.EditText>(R.id.serverUrlInput).text.toString().trim()
            if (url.isBlank()) {
                Toast.makeText(this, "URL cannot be empty", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            val normalized = if (url.startsWith("http")) url else "http://$url"
            prefs.edit().putString("server_url", normalized).apply()
            setResult(RESULT_OK, Intent().putExtra("server_url", normalized))
            finish()
        }
    }
}
