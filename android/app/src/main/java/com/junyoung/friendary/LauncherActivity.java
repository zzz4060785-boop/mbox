package com.junyoung.friendary;

/**
 * Launches the website as a Trusted Web Activity. Play Billing's Digital
 * Goods API is exposed by Chrome only while the site runs inside a verified
 * TWA, so this must not be replaced with a plain WebView Activity.
 */
public class LauncherActivity
        extends com.google.androidbrowserhelper.trusted.LauncherActivity {
}
