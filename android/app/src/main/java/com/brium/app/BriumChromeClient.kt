package com.brium.app

import android.webkit.WebChromeClient
import android.webkit.WebView

class BriumChromeClient : WebChromeClient() {

    override fun onProgressChanged(view: WebView?, newProgress: Int) {
        super.onProgressChanged(view, newProgress)
    }
}
