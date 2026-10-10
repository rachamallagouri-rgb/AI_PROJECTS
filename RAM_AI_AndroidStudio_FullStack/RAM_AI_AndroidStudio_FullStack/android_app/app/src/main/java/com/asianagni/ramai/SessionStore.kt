package com.asianagni.ramai

import android.content.Context

class SessionStore(context: Context) {
    private val prefs = context.getSharedPreferences("ram_ai_session", Context.MODE_PRIVATE)

    var token: String?
        get() = prefs.getString("token", null)
        set(value) = prefs.edit().putString("token", value).apply()

    fun clear() = prefs.edit().clear().apply()
}
