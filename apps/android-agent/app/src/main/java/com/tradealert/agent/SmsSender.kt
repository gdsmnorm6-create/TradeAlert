package com.tradealert.agent

import android.telephony.SmsManager

object SmsSender {
    @Suppress("DEPRECATION")
    fun send(toNumber: String, body: String): String {
        val manager = SmsManager.getDefault()
        val parts = manager.divideMessage(body)
        if (parts.size <= 1) {
            manager.sendTextMessage(toNumber, null, body, null, null)
        } else {
            manager.sendMultipartTextMessage(toNumber, null, ArrayList(parts), null, null)
        }
        return "android-sms-${System.currentTimeMillis()}"
    }
}
