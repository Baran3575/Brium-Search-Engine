package com.brium.app

import android.annotation.SuppressLint
import android.content.Intent
import android.graphics.Bitmap
import android.net.http.SslError
import android.os.Bundle
import android.view.KeyEvent
import android.view.View
import android.view.inputmethod.EditorInfo
import android.webkit.SslErrorHandler
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.EditText
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.webkit.WebSettingsCompat
import androidx.webkit.WebViewFeature
import com.google.android.material.appbar.MaterialToolbar

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var progressBar: ProgressBar
    private lateinit var errorView: LinearLayout
    private lateinit var errorMessage: TextView
    private lateinit var urlBar: EditText
    private lateinit var navBack: ImageButton
    private lateinit var navForward: ImageButton
    private lateinit var navRefresh: ImageButton

    private var currentUrl: String? = null

    private val settingsLauncher = registerForActivityResult(
        androidx.activity.result.contract.ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == RESULT_OK) {
            val newUrl = result.data?.getStringExtra("server_url")
            if (newUrl != null && newUrl != currentUrl) {
                currentUrl = newUrl
                if (::webView.isInitialized) {
                    loadUrl(currentUrl!!)
                }
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = getSharedPreferences("brium", MODE_PRIVATE)
        val serverUrl = prefs.getString("server_url", null)
        if (serverUrl.isNullOrBlank()) {
            showSettings()
        } else {
            currentUrl = serverUrl
            showBrowser()
        }
    }

    private fun showSettings() {
        val intent = Intent(this, SettingsActivity::class.java)
        settingsLauncher.launch(intent)
    }

    private fun showSetupIfNeeded() {
        val prefs = getSharedPreferences("brium", MODE_PRIVATE)
        val serverUrl = prefs.getString("server_url", null)
        if (serverUrl.isNullOrBlank()) {
            showSettings()
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun showBrowser() {
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webView)
        progressBar = findViewById(R.id.progressBar)
        errorView = findViewById(R.id.errorView)
        errorMessage = findViewById(R.id.errorMessage)
        urlBar = findViewById(R.id.urlBar)
        navBack = findViewById(R.id.navBack)
        navForward = findViewById(R.id.navForward)
        navRefresh = findViewById(R.id.navRefresh)

        findViewById<ImageButton>(R.id.settingsButton).setOnClickListener {
            settingsLauncher.launch(Intent(this, SettingsActivity::class.java))
        }

        navBack.setOnClickListener {
            if (webView.canGoBack()) webView.goBack()
        }

        navForward.setOnClickListener {
            if (webView.canGoForward()) webView.goForward()
        }

        navRefresh.setOnClickListener {
            webView.reload()
        }

        urlBar.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_GO) {
                val input = urlBar.text.toString().trim()
                if (input.isNotBlank()) {
                    loadInWebView(input)
                }
                urlBar.clearFocus()
                hideKeyboard()
                true
            } else false
        }

        urlBar.setOnFocusChangeListener { _, hasFocus ->
            if (hasFocus) {
                urlBar.selectAll()
            }
        }

        findViewById<View>(R.id.retryButton).setOnClickListener {
            currentUrl?.let { loadUrl(it) }
        }

        findViewById<View>(R.id.changeServerButton).setOnClickListener {
            getSharedPreferences("brium", MODE_PRIVATE)
                .edit()
                .remove("server_url")
                .apply()
            showSettings()
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
                        return false
                    }
                    return false
                }

                override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                    url?.let { urlBar.setText(it) }
                    progressBar.visibility = View.VISIBLE
                    progressBar.progress = 0
                    updateNavButtons()
                }

                override fun onPageFinished(view: WebView?, url: String?) {
                    progressBar.progress = 100
                    progressBar.visibility = View.GONE
                    errorView.visibility = View.GONE
                    webView.visibility = View.VISIBLE
                    updateNavButtons()
                }

                override fun onReceivedError(
                    view: WebView?,
                    errorCode: Int,
                    description: String?,
                    failingUrl: String?
                ) {
                    progressBar.visibility = View.GONE
                    if (failingUrl == currentUrl || errorCode == ERROR_HOST_LOOKUP) {
                        showError(getString(R.string.connection_error), "$failingUrl\n$description")
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
            loadUrl(currentUrl!!)
        } catch (e: Exception) {
            showError("Error", e.message ?: "Unknown error")
        }
    }

    private fun loadInWebView(input: String) {
        val url = if (input.startsWith("http://") || input.startsWith("https://")) {
            input
        } else if (input.contains(".") && !input.contains(" ")) {
            "http://$input"
        } else {
            currentUrl?.let { base ->
                val separator = if (base.contains("?")) "&" else "?"
                "$base$separator${android.net.Uri.encode("q")}=${android.net.Uri.encode(input)}"
            } ?: return
        }
        loadUrl(url)
    }

    private fun loadUrl(url: String) {
        showSetupIfNeeded()
        errorView.visibility = View.GONE
        webView.visibility = View.VISIBLE
        webView.loadUrl(url)
    }

    private fun showError(title: String, message: String) {
        webView.visibility = View.GONE
        errorView.visibility = View.VISIBLE
        errorMessage.text = "$title\n$message"
    }

    private fun updateNavButtons() {
        navBack.isEnabled = webView.canGoBack()
        navForward.isEnabled = webView.canGoForward()
        navBack.alpha = if (webView.canGoBack()) 1f else 0.3f
        navForward.alpha = if (webView.canGoForward()) 1f else 0.3f
    }

    private fun hideKeyboard() {
        val imm = getSystemService(INPUT_METHOD_SERVICE) as android.view.inputmethod.InputMethodManager
        imm.hideSoftInputFromWindow(urlBar.windowToken, 0)
    }

    fun openUrlInApp(url: String) {
        loadUrl(url)
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            if (webView.canGoBack()) {
                webView.goBack()
                return true
            }
            showSetupIfNeeded()
        }
        return super.onKeyDown(keyCode, event)
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        if (::webView.isInitialized) webView.saveState(outState)
    }

    override fun onRestoreInstanceState(savedInstanceState: Bundle) {
        super.onRestoreInstanceState(savedInstanceState)
        if (::webView.isInitialized) webView.restoreState(savedInstanceState)
    }

    override fun onResume() {
        super.onResume()
        val prefs = getSharedPreferences("brium", MODE_PRIVATE)
        val saved = prefs.getString("server_url", null)
        if (saved.isNullOrBlank()) {
            showSettings()
            return
        }
        if (currentUrl == null) {
            currentUrl = saved
            if (::webView.isInitialized) loadUrl(currentUrl!!)
        }
    }
}
