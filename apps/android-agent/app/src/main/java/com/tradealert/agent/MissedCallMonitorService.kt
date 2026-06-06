package com.tradealert.agent

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.PackageManager
import android.database.Cursor
import android.net.Uri
import android.os.Build
import android.os.IBinder
import android.provider.CallLog
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.TimeUnit

class MissedCallMonitorService : Service() {
    private val executor: ScheduledExecutorService = Executors.newSingleThreadScheduledExecutor()

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, notification())
        executor.scheduleWithFixedDelay({ scanSafely() }, 0, 30, TimeUnit.SECONDS)
        AgentLog.add(this, "Monitor service started")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            Prefs.setMonitoringEnabled(this, false)
            AgentLog.add(this, "Monitor stopped")
            stopSelf()
            return START_NOT_STICKY
        }
        Prefs.setMonitoringEnabled(this, true)
        return START_STICKY
    }

    override fun onDestroy() {
        executor.shutdownNow()
        AgentLog.add(this, "Monitor service destroyed")
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun scanSafely() {
        try {
            scanOnce()
        } catch (error: Throwable) {
            AgentLog.add(this, "Monitor error: ${error.message}")
        }
    }

    private fun scanOnce() {
        if (!Prefs.isMonitoringEnabled(this)) return

        if (!hasRequiredPermissions()) {
            AgentLog.add(this, "Waiting for call-log and SMS permissions")
            return
        }

        val apiBase = Prefs.apiBase(this)
        val token = Prefs.token(this)
        if (apiBase.isBlank() || token.isBlank()) {
            AgentLog.add(this, "API URL or agent token missing")
            return
        }

        val api = AgentApi(apiBase)
        heartbeatIfNeeded(api, token)
        sendPendingMessages(api, token)

        val events = loadNewMissedCalls()
        for (event in events) {
            val processed = processMissedCall(api, token, event)
            if (!processed) break
            markLastCallId(event.callLogId)
        }
    }

    private fun hasRequiredPermissions(): Boolean =
        checkSelfPermission(Manifest.permission.READ_CALL_LOG) == PackageManager.PERMISSION_GRANTED &&
            checkSelfPermission(Manifest.permission.SEND_SMS) == PackageManager.PERMISSION_GRANTED

    private fun heartbeatIfNeeded(api: AgentApi, token: String) {
        val prefs = Prefs.get(this)
        val now = System.currentTimeMillis()
        val lastHeartbeat = prefs.getLong(Prefs.KEY_LAST_HEARTBEAT_AT, 0)
        if (now - lastHeartbeat < TimeUnit.MINUTES.toMillis(10)) return
        api.heartbeat(token)
        prefs.edit().putLong(Prefs.KEY_LAST_HEARTBEAT_AT, now).apply()
    }

    private fun sendPendingMessages(api: AgentApi, token: String) {
        val pending = api.pendingMessages(token)
        for (task in pending) {
            sendSmsTask(api, token, task)
        }
    }

    private fun loadNewMissedCalls(): List<MissedCallEvent> {
        val prefs = Prefs.get(this)
        val lastCallId = prefs.getLong(Prefs.KEY_LAST_CALL_ID, 0)
        val events = mutableListOf<MissedCallEvent>()
        var highestSeenId = lastCallId

        val projection = arrayOf(
            CallLog.Calls._ID,
            CallLog.Calls.NUMBER,
            CallLog.Calls.TYPE,
            CallLog.Calls.DATE,
        )

        contentResolver.query(
            CallLog.Calls.CONTENT_URI,
            projection,
            null,
            null,
            "${CallLog.Calls.DATE} DESC",
        )?.use { cursor ->
            var checked = 0
            while (cursor.moveToNext() && checked < 40) {
                checked += 1
                val id = cursor.long(CallLog.Calls._ID)
                highestSeenId = maxOf(highestSeenId, id)
                if (id <= lastCallId) continue
                val type = cursor.int(CallLog.Calls.TYPE)
                if (type != CallLog.Calls.MISSED_TYPE) continue
                val number = cursor.string(CallLog.Calls.NUMBER)
                val dateMillis = cursor.long(CallLog.Calls.DATE)
                events.add(
                    MissedCallEvent(
                        callLogId = id,
                        callerNumber = number,
                        missedAtIso = isoTime(dateMillis),
                        simNumber = Prefs.phone(this),
                    )
                )
            }
        }

        if (lastCallId == 0L && highestSeenId > 0) {
            prefs.edit().putLong(Prefs.KEY_LAST_CALL_ID, highestSeenId).apply()
            AgentLog.add(this, "Call-log baseline set at $highestSeenId")
            return emptyList()
        }

        return events.sortedBy { it.callLogId }
    }

    private fun processMissedCall(api: AgentApi, token: String, event: MissedCallEvent): Boolean {
        if (!PhoneSafety.isSafeSmsDestination(event.callerNumber)) {
            AgentLog.add(this, "Skipped unsafe caller ${event.callerNumber}")
            return true
        }

        if (isInCooldown(event.callerNumber)) {
            AgentLog.add(this, "Skipped ${event.callerNumber}: cooldown active")
            return true
        }

        return try {
            AgentLog.add(this, "Missed call from ${event.callerNumber}")
            val result = api.reportMissedCall(token, event)
            if (result.alreadyProcessed) {
                AgentLog.add(this, "Backend already processed call ${event.callLogId}")
                true
            } else {
                val task = result.sms
                if (task == null) {
                    AgentLog.add(this, "Backend logged call ${event.callLogId} with no SMS task")
                    true
                } else {
                    sendSmsTask(api, token, task)
                    setCooldown(event.callerNumber)
                    true
                }
            }
        } catch (error: Throwable) {
            AgentLog.add(this, "Could not process call ${event.callLogId}: ${error.message}")
            false
        }
    }

    private fun sendSmsTask(api: AgentApi, token: String, task: SmsTask) {
        if (!PhoneSafety.isSafeSmsDestination(task.toNumber)) {
            api.reportDelivery(token, task.messageId, "failed", error = "unsafe_destination")
            AgentLog.add(this, "Refused unsafe SMS destination ${task.toNumber}")
            return
        }

        if (Prefs.hasSentMessage(this, task.messageId)) {
            api.reportDelivery(token, task.messageId, "sent", providerSid = "android-sms-reconciled")
            AgentLog.add(this, "Reconciled already sent message ${task.messageId}")
            return
        }

        try {
            val providerSid = SmsSender.send(task.toNumber, task.body)
            Prefs.markMessageSent(this, task.messageId)
            api.reportDelivery(token, task.messageId, "sent", providerSid = providerSid)
            AgentLog.add(this, "Sent SMS to ${task.toNumber}")
        } catch (error: Throwable) {
            api.reportDelivery(token, task.messageId, "failed", error = error.message)
            AgentLog.add(this, "SMS failed for ${task.toNumber}: ${error.message}")
        }
    }

    private fun isInCooldown(number: String): Boolean {
        val prefs = Prefs.get(this)
        val key = cooldownKey(number)
        val lastSentAt = prefs.getLong(key, 0)
        return System.currentTimeMillis() - lastSentAt < COOLDOWN_MS
    }

    private fun setCooldown(number: String) {
        Prefs.get(this).edit().putLong(cooldownKey(number), System.currentTimeMillis()).apply()
    }

    private fun cooldownKey(number: String): String =
        "cooldown_${number.filter { it.isLetterOrDigit() }}"

    private fun markLastCallId(id: Long) {
        val prefs = Prefs.get(this)
        val current = prefs.getLong(Prefs.KEY_LAST_CALL_ID, 0)
        if (id > current) {
            prefs.edit().putLong(Prefs.KEY_LAST_CALL_ID, id).apply()
        }
    }

    private fun Cursor.long(column: String): Long =
        getLong(getColumnIndexOrThrow(column))

    private fun Cursor.int(column: String): Int =
        getInt(getColumnIndexOrThrow(column))

    private fun Cursor.string(column: String): String =
        getString(getColumnIndexOrThrow(column)).orEmpty()

    private fun isoTime(dateMillis: Long): String {
        val format = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.UK)
        format.timeZone = TimeZone.getTimeZone("UTC")
        return format.format(Date(dateMillis))
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val channel = NotificationChannel(
            CHANNEL_ID,
            "TradeAlert monitoring",
            NotificationManager.IMPORTANCE_LOW,
        )
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }

    private fun notification(): Notification {
        val intent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        return Notification.Builder(this, CHANNEL_ID)
            .setContentTitle("TradeAlert Agent")
            .setContentText("Watching missed calls")
            .setSmallIcon(android.R.drawable.sym_call_missed)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    companion object {
        const val ACTION_STOP = "com.tradealert.agent.STOP"
        private const val CHANNEL_ID = "tradealert_monitor"
        private const val NOTIFICATION_ID = 6101
        private val COOLDOWN_MS = TimeUnit.MINUTES.toMillis(30)
    }
}
