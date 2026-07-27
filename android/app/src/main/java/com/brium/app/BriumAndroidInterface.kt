package com.brium.app

import android.webkit.JavascriptInterface

class BriumAndroidInterface(private val activity: MainActivity) {

    @JavascriptInterface
    fun openInApp(url: String) {
        activity.runOnUiThread {
            activity.openUrlInApp(url)
        }
    }
}
