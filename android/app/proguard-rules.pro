-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}

-keepclassmembers class com.brium.app.BriumAndroidInterface {
    public *;
}

-dontwarn android.webkit.**
-keep class android.webkit.** { *; }
