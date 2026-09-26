package com.smartfinance.tracker.storage

import android.content.Context
import android.content.SharedPreferences

class AppPreferences(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    var backendBaseUrl: String
        get() = prefs.getString(KEY_BACKEND_URL, DEFAULT_URL) ?: DEFAULT_URL
        set(value) {
            val sanitized = if (!value.endsWith("/")) "$value/" else value
            prefs.edit().putString(KEY_BACKEND_URL, sanitized).apply()
        }

    var studentId: Int
        get() = prefs.getInt(KEY_STUDENT_ID, DEFAULT_STUDENT_ID)
        set(value) = prefs.edit().putInt(KEY_STUDENT_ID, value).apply()

    var isAutoDetectionEnabled: Boolean
        get() = prefs.getBoolean(KEY_AUTO_DETECT_ENABLED, true)
        set(value) = prefs.edit().putBoolean(KEY_AUTO_DETECT_ENABLED, value).apply()

    var lastDetectedSummary: String?
        get() = prefs.getString(KEY_LAST_DETECTED, null)
        set(value) = prefs.edit().putString(KEY_LAST_DETECTED, value).apply()

    var lastDetectedTimestamp: Long
        get() = prefs.getLong(KEY_LAST_DETECTED_TIME, 0L)
        set(value) = prefs.edit().putLong(KEY_LAST_DETECTED_TIME, value).apply()

    companion object {
        private const val PREFS_NAME = "smart_finance_tracker_prefs"
        private const val KEY_BACKEND_URL = "backend_base_url"
        private const val KEY_STUDENT_ID = "student_id"
        private const val KEY_AUTO_DETECT_ENABLED = "auto_detect_enabled"
        private const val KEY_LAST_DETECTED = "last_detected_summary"
        private const val KEY_LAST_DETECTED_TIME = "last_detected_timestamp"

        // Default backend URL points to production server deployed on Render.
        // Can be customized in app settings dialog if running custom server.
        const val DEFAULT_URL = "https://ai-personal-finance-tracker-7qp8.onrender.com/"
        const val DEFAULT_STUDENT_ID = 1
    }
}
