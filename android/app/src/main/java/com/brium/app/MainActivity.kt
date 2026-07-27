package com.brium.app

import android.annotation.SuppressLint
import android.content.Intent
import android.graphics.Bitmap
import android.net.http.SslError
import android.os.Bundle
import android.view.KeyEvent
import android.view.View
import android.webkit.SslErrorHandler
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.webkit.WebSettingsCompat
import androidx.webkit.WebViewFeature

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var progressBar: ProgressBar
    private lateinit var errorView: LinearLayout
    private lateinit var errorMessage: TextView

    private var currentUrl: String? = null

    private val settingsLauncher = registerForActivityResult(
        androidx.activity.result.contract.ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == RESULT_OK) {
            val newUrl = result.data?.getStringExtra("server_url")
            if (newUrl != null && newUrl != currentUrl) {
                currentUrl = newUrl
                if (::webView.isInitialized) {
                    loadServerUrl()
                }
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val prefs = getSharedPreferences("brium", MODE_PRIVATE)
        val serverUrl = prefs.getString("server_url", null)

        if (serverUrl.isNullOrBlank()) {
            showSetupScreen()
        } else {
            currentUrl = serverUrl
            showMainScreen()
        }
    }

    private fun showSetupScreen() {
        setContentView(R.layout.activity_setup)

        val input = findViewById<EditText>(R.id.serverUrlInput)
        val connect = findViewById<Button>(R.id.connectButton)

        connect.setOnClickListener {
            val url = input.text.toString().trim()
            if (url.isBlank()) {
                input.error = "Enter a server URL"
                return@setOnClickListener
            }
            val normalized = if (url.startsWith("http")) url else "http://$url"
            getSharedPreferences("brium", MODE_PRIVATE)
                .edit()
                .putString("server_url", normalized)
                .apply()
            currentUrl = normalized
            showMainScreen()
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun showMainScreen() {
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webView)
        progressBar = findViewById(R.id.progressBar)
        errorView = findViewById(R.id.errorView)
        errorMessage = findViewById(R.id.errorMessage)

        val toolbar = findViewById<androidx.appcompat.widget.Toolbar>(R.id.toolbar)
        setSupportActionBar(toolbar)
        supportActionBar?.setDisplayShowTitleEnabled(false)

        findViewById<ImageButton>(R.id.settingsButton).setOnClickListener {
            settingsLauncher.launch(Intent(this, SettingsActivity::class.java))
        }

        findViewById<ImageButton>(R.id.refreshButton).setOnClickListener {
            webView.reload()
        }

        findViewById<Button>(R.id.retryButton).setOnClickListener {
            loadServerUrl()
        }

        findViewById<Button>(R.id.changeServerButton).setOnClickListener {
            getSharedPreferences("brium", MODE_PRIVATE)
                .edit()
                .remove("server_url")
                .apply()
            showSetupScreen()
        }

        try {
            webView.addJavascriptInterface(BriumAndroidInterface(this), "BriumAndroid")

            with(webView.settings) {
                javaScriptEnabled = true
                domStorageEnabled = true
                useWideViewPort = true
                loadWithOverviewMode = true
                builtInZoomControls = true
                displayZoomControls = false
                setSupportZoom(true)
                allowFileAccess = false
                allowContentAccess = false
                mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
                cacheMode = android.webkit.WebSettings.LOAD_DEFAULT
            }

            if (WebViewFeature.isFeatureSupported(WebViewFeature.FORCE_DARK)) {
                WebSettingsCompat.setForceDark(
                    webView.settings,
                    WebSettingsCompat.FORCE_DARK_AUTO
                )
            }

            webView.webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(
                    view: WebView,
                    request: WebResourceRequest
                ): Boolean {
                    val url = request.url.toString()
                    if (url.startsWith("http://") || url.startsWith("https://")) {
                        view.loadUrl(url)
                        return true
                    }
                    return false
                }

                override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                    progressBar.visibility = View.VISIBLE
                    progressBar.progress = 0
                }

                override fun onPageFinished(view: WebView?, url: String?) {
                    progressBar.progress = 100
                    progressBar.visibility = View.GONE
                    errorView.visibility = View.GONE
                }

                override fun onReceivedError(
                    view: WebView?,
                    errorCode: Int,
                    description: String?,
                    failingUrl: String?
                ) {
                    progressBar.visibility = View.GONE
                    if (failingUrl == currentUrl || errorCode == ERROR_HOST_LOOKUP) {
                        showError("Could not reach server at\n$failingUrl")
                    }
                }

                override fun onReceivedSslError(
                    view: WebView?,
                    handler: SslErrorHandler?,
                    error: SslError?
                ) {
                    handler?.proceed()
                }
            }

            webView.webChromeClient = BriumChromeClient(progressBar)

            loadServerUrl()
        } catch (e: Exception) {
            showError("Failed to initialize: ${e.message}")
        }
    }

    private fun loadServerUrl() {
        errorView.visibility = View.GONE
        webView.visibility = View.VISIBLE
        currentUrl?.let { webView.loadUrl(it) }
    }

    private fun showError(message: String) {
        webView.visibility = View.GONE
        errorView.visibility = View.VISIBLE
        errorMessage.text = message
    }

    fun openUrlInApp(url: String) {
        webView.loadUrl(url)
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        if (keyCode == KeyEvent.KEYCODE_BACK && webView.canGoBack()) {
            webView.goBack()
            return true
        }
        return super.onKeyDown(keyCode, event)
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        if (::webView.isInitialized) {
            webView.saveState(outState)
        }
    }

    override fun onRestoreInstanceState(savedInstanceState: Bundle) {
        super.onRestoreInstanceState(savedInstanceState)
        if (::webView.isInitialized) {
            webView.restoreState(savedInstanceState)
        }
    }

    override fun onResume() {
        super.onResume()
        val prefs = getSharedPreferences("brium", MODE_PRIVATE)
        val saved = prefs.getString("server_url", null)
        if (saved.isNullOrBlank()) {
            if (::webView.isInitialized) {
                showSetupScreen()
            }
            return
        }
        if (currentUrl == null) {
            currentUrl = saved
        }
        if (::webView.isInitialized && webView.url == null) {
            loadServerUrl()
        }
    }
}
