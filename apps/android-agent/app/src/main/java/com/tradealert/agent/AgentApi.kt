package com.tradealert.agent

import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

data class RegisterResult(
    val agentId: String,
    val token: String,
    val companyId: String,
    val businessPhone: String,
)

data class SmsTask(
    val messageId: String,
    val toNumber: String,
    val body: String,
)

data class MissedCallEvent(
    val callLogId: Long,
    val callerNumber: String,
    val missedAtIso: String,
    val simNumber: String,
)

data class MissedCallResult(
    val alreadyProcessed: Boolean,
    val sms: SmsTask?,
)

class AgentApi(private val baseUrl: String) {
    fun login(email: String, password: String): String {
        val body = JSONObject()
            .put("email", email)
            .put("password", password)
        val response = request("POST", "/api/auth/login", body = body)
        return JSONObject(response).getString("access_token")
    }

    fun registerAgent(accessToken: String, phoneNumber: String): RegisterResult {
        val body = JSONObject()
            .put("name", "Hermes Android Agent")
            .put("platform", "android")
            .put("phone_number", phoneNumber)
        val response = request(
            "POST",
            "/api/device-agent/register",
            headers = mapOf("Authorization" to "Bearer $accessToken"),
            body = body,
        )
        val json = JSONObject(response)
        return RegisterResult(
            agentId = json.getString("agent_id"),
            token = json.getString("token"),
            companyId = json.getString("company_id"),
            businessPhone = json.getString("business_phone"),
        )
    }

    fun heartbeat(agentToken: String) {
        request("POST", "/api/device-agent/heartbeat", agentHeaders(agentToken))
    }

    fun pendingMessages(agentToken: String): List<SmsTask> {
        val response = request("GET", "/api/device-agent/pending-messages", agentHeaders(agentToken))
        val json = JSONArray(response)
        return (0 until json.length()).map { index ->
            json.getJSONObject(index).toSmsTask()
        }
    }

    fun reportMissedCall(agentToken: String, event: MissedCallEvent): MissedCallResult {
        val rawPayload = JSONObject()
            .put("android_call_log_id", event.callLogId)
        val body = JSONObject()
            .put("caller_number", event.callerNumber)
            .put("device_call_id", event.callLogId.toString())
            .put("missed_at", event.missedAtIso)
            .put("sim_number", event.simNumber)
            .put("raw_payload", rawPayload)
        val response = request("POST", "/api/device-agent/missed-call", agentHeaders(agentToken), body)
        val json = JSONObject(response)
        return MissedCallResult(
            alreadyProcessed = json.optBoolean("already_processed", false),
            sms = json.optJSONObject("sms")?.toSmsTask(),
        )
    }

    fun reportDelivery(
        agentToken: String,
        messageId: String,
        status: String,
        providerSid: String? = null,
        error: String? = null,
    ) {
        val body = JSONObject()
            .put("status", status)
            .put("provider_sid", providerSid ?: JSONObject.NULL)
            .put("error", error ?: JSONObject.NULL)
        request(
            "POST",
            "/api/device-agent/messages/$messageId/delivery",
            agentHeaders(agentToken),
            body,
        )
    }

    private fun agentHeaders(agentToken: String): Map<String, String> =
        mapOf("X-TradeAlert-Agent-Token" to agentToken)

    private fun JSONObject.toSmsTask(): SmsTask =
        SmsTask(
            messageId = getString("message_id"),
            toNumber = getString("to_number"),
            body = getString("body"),
        )

    private fun request(
        method: String,
        path: String,
        headers: Map<String, String> = emptyMap(),
        body: JSONObject? = null,
    ): String {
        val url = URL("${baseUrl.trimEnd('/')}$path")
        val connection = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 10_000
            readTimeout = 20_000
            setRequestProperty("Accept", "application/json")
            headers.forEach { (name, value) -> setRequestProperty(name, value) }
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
                outputStream.use { stream ->
                    stream.write(body.toString().toByteArray(Charsets.UTF_8))
                }
            }
        }

        val statusCode = connection.responseCode
        val stream = if (statusCode in 200..299) connection.inputStream else connection.errorStream
        val response = stream?.use { input ->
            BufferedReader(InputStreamReader(input)).readText()
        }.orEmpty()
        connection.disconnect()

        if (statusCode !in 200..299) {
            throw IllegalStateException("HTTP $statusCode from $path: $response")
        }
        return response
    }
}
