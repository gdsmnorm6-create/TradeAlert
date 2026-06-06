package com.tradealert.agent

import android.content.Context
import android.util.Log
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object AgentLog {
    private const val TAG = "TradeAlertAgent"
    private const val MAX_LINES = 80

    @Synchronized
    fun add(context: Context, message: String) {
        Log.i(TAG, message)
        val stamp = SimpleDateFormat("HH:mm:ss", Locale.UK).format(Date())
        val line = "$stamp  $message"
        val prefs = Prefs.get(context)
        val existing = prefs.getString(Prefs.KEY_LOG_LINES, "").orEmpty()
        val lines = (listOf(line) + existing.lines().filter { it.isNotBlank() }).take(MAX_LINES)
        prefs.edit().putString(Prefs.KEY_LOG_LINES, lines.joinToString("\n")).apply()
    }

    fun text(context: Context): String =
        Prefs.get(context).getString(Prefs.KEY_LOG_LINES, "").orEmpty()
}
