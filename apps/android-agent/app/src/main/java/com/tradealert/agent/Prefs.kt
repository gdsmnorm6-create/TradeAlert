package com.tradealert.agent

import android.content.Context
import android.content.SharedPreferences

object Prefs {
    private const val FILE_NAME = "tradealert_agent"

    const val KEY_API_BASE = "api_base"
    const val KEY_EMAIL = "email"
    const val KEY_PHONE = "phone"
    const val KEY_AGENT_TOKEN = "agent_token"
    const val KEY_MONITORING_ENABLED = "monitoring_enabled"
    const val KEY_LAST_CALL_ID = "last_call_id"
    const val KEY_LAST_HEARTBEAT_AT = "last_heartbeat_at"
    const val KEY_LOG_LINES = "log_lines"
    const val KEY_SENT_MESSAGE_IDS = "sent_message_ids"

    fun get(context: Context): SharedPreferences =
        context.getSharedPreferences(FILE_NAME, Context.MODE_PRIVATE)

    fun apiBase(context: Context): String =
        get(context).getString(KEY_API_BASE, "")?.trim().orEmpty().trimEnd('/')

    fun token(context: Context): String =
        get(context).getString(KEY_AGENT_TOKEN, "")?.trim().orEmpty()

    fun phone(context: Context): String =
        get(context).getString(KEY_PHONE, "")?.trim().orEmpty()

    fun isMonitoringEnabled(context: Context): Boolean =
        get(context).getBoolean(KEY_MONITORING_ENABLED, false)

    fun setMonitoringEnabled(context: Context, enabled: Boolean) {
        get(context).edit().putBoolean(KEY_MONITORING_ENABLED, enabled).apply()
    }

    fun hasSentMessage(context: Context, messageId: String): Boolean =
        get(context).getStringSet(KEY_SENT_MESSAGE_IDS, emptySet())?.contains(messageId) == true

    fun markMessageSent(context: Context, messageId: String) {
        val prefs = get(context)
        val current = prefs.getStringSet(KEY_SENT_MESSAGE_IDS, emptySet()).orEmpty().toMutableSet()
        current.add(messageId)
        while (current.size > 200) {
            current.remove(current.first())
        }
        prefs.edit().putStringSet(KEY_SENT_MESSAGE_IDS, current).apply()
    }
}
