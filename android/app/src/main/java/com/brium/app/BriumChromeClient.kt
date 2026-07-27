package com.brium.app

import android.webkit.WebChromeClient
import android.webkit.WebView
import android.widget.ProgressBar

class BriumChromeClient(private val progressBar: ProgressBar) : WebChromeClient() {

    override fun onProgressChanged(view: WebView?, newProgress: Int) {
        super.onProgressChanged(view, newProgress)
        progressBar.progress = newProgress
        if (newProgress == 100) {
            progressBar.visibility = android.view.View.GONE
        } else {
            progressBar.visibility = android.view.View.VISIBLE
        }
    }
}
