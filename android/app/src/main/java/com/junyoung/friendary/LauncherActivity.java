package com.junyoung.friendary;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.Bundle;
import android.os.Message;
import android.net.Uri;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.view.Window;
import android.graphics.Color;
import android.content.pm.ApplicationInfo;
import androidx.core.view.WindowCompat;

public class LauncherActivity extends Activity {
    private static final int FILE_CHOOSER_REQUEST = 1001;
    private static final int CACHE_SCHEMA_VERSION = 2;
    private WebView mWebView;
    private ValueCallback<Uri[]> mFileChooserCallback;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);

        // Android 15+ defaults apps to edge-to-edge. Friendary's web layout is
        // not a fullscreen surface, so keep it inside the system-bar insets.
        WindowCompat.setDecorFitsSystemWindows(getWindow(), true);
        getWindow().setStatusBarColor(Color.BLACK);
        getWindow().setNavigationBarColor(Color.BLACK);

        mWebView = new WebView(this);
        setContentView(mWebView);

        // Clear the HTTP cache once after an app upgrade that changes the web
        // shell. Cookies and login sessions are intentionally preserved.
        SharedPreferences cachePreferences = getSharedPreferences("friendary_webview", MODE_PRIVATE);
        if (cachePreferences.getInt("cache_schema", 0) < CACHE_SCHEMA_VERSION) {
            mWebView.clearCache(true);
            cachePreferences.edit().putInt("cache_schema", CACHE_SCHEMA_VERSION).apply();
        }

        boolean isDebuggable = (getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0;
        if (isDebuggable && Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
            WebView.setWebContentsDebuggingEnabled(true);
        }

        WebSettings webSettings = mWebView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webSettings.setDatabaseEnabled(true);
        webSettings.setUseWideViewPort(true);
        webSettings.setLoadWithOverviewMode(true);
        webSettings.setAllowFileAccess(false);
        // Needed only for content:// URIs explicitly selected by Android's
        // system picker. Direct filesystem access remains disabled above.
        webSettings.setAllowContentAccess(true);
        webSettings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            webSettings.setSafeBrowsingEnabled(true);
        }
        webSettings.setCacheMode(WebSettings.LOAD_DEFAULT);

        mWebView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return false;
            }

            @Override
            public void onFormResubmission(WebView view, Message dontResend, Message resend) {
                resend.sendToTarget();
            }
        });

        mWebView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(
                    WebView webView,
                    ValueCallback<Uri[]> filePathCallback,
                    FileChooserParams fileChooserParams) {
                if (mFileChooserCallback != null) {
                    mFileChooserCallback.onReceiveValue(null);
                }
                mFileChooserCallback = filePathCallback;

                Intent chooserIntent;
                try {
                    chooserIntent = fileChooserParams.createIntent();
                    chooserIntent.addCategory(Intent.CATEGORY_OPENABLE);
                    startActivityForResult(chooserIntent, FILE_CHOOSER_REQUEST);
                    return true;
                } catch (Exception error) {
                    mFileChooserCallback = null;
                    return false;
                }
            }
        });

        mWebView.loadUrl("https://zzz8247.mycafe24.com/");
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == FILE_CHOOSER_REQUEST) {
            if (mFileChooserCallback != null) {
                Uri[] selectedFiles = WebChromeClient.FileChooserParams.parseResult(
                        resultCode,
                        data);
                mFileChooserCallback.onReceiveValue(selectedFiles);
                mFileChooserCallback = null;
            }
            return;
        }
        super.onActivityResult(requestCode, resultCode, data);
    }

    @Override
    public void onBackPressed() {
        if (mWebView != null && mWebView.canGoBack()) {
            mWebView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
