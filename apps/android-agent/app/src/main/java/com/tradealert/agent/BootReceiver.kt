package com.tradealert.agent

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        if (!Prefs.isMonitoringEnabled(context)) return
        if (Prefs.apiBase(context).isBlank() || Prefs.token(context).isBlank()) return

        val serviceIntent = Intent(context, MissedCallMonitorService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(serviceIntent)
        } else {
            context.startService(serviceIntent)
        }
        AgentLog.add(context, "Monitor restarted after boot")
    }
}
