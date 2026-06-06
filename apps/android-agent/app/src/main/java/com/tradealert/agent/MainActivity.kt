package com.tradealert.agent

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.text.InputType
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

class MainActivity : Activity() {
    private lateinit var apiBaseInput: EditText
    private lateinit var emailInput: EditText
    private lateinit var passwordInput: EditText
    private lateinit var phoneInput: EditText
    private lateinit var tokenInput: EditText
    private lateinit var statusText: TextView
    private lateinit var logText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        loadPrefs()
        refreshStatus()
    }

    override fun onResume() {
        super.onResume()
        refreshStatus()
    }

    private fun buildUi() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 32, 32, 32)
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
            )
        }

        root.addView(title("TradeAlert Agent"))
        statusText = body("")
        root.addView(statusText)

        apiBaseInput = input("API base URL, for example http://100.x.x.x:8000")
        emailInput = input("TradeAlert email")
        passwordInput = input("TradeAlert password").apply {
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
        }
        phoneInput = input("This phone number, for example 07432870739")
        tokenInput = input("Agent token").apply {
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD
        }

        root.addView(label("API URL"))
        root.addView(apiBaseInput)
        root.addView(label("Email"))
        root.addView(emailInput)
        root.addView(label("Password"))
        root.addView(passwordInput)
        root.addView(label("Phone/SIM number"))
        root.addView(phoneInput)
        root.addView(label("Agent token"))
        root.addView(tokenInput)

        root.addView(button("Save settings") {
            savePrefs()
            refreshStatus()
        })
        root.addView(button("Allow permissions") {
            requestNeededPermissions()
        })
        root.addView(button("Login and register this phone") {
            savePrefs()
            registerAgent()
        })
        root.addView(button("Start missed-call monitoring") {
            savePrefs()
            startMonitoring()
        })
        root.addView(button("Stop monitoring") {
            stopMonitoring()
        })
        root.addView(button("Heartbeat test") {
            savePrefs()
            heartbeatTest()
        })
        root.addView(button("Refresh log") {
            refreshStatus()
        })

        root.addView(label("Agent log"))
        logText = body("")
        root.addView(logText)

        setContentView(ScrollView(this).apply { addView(root) })
    }

    private fun title(text: String): TextView =
        TextView(this).apply {
            this.text = text
            textSize = 24f
            setPadding(0, 0, 0, 16)
        }

    private fun label(text: String): TextView =
        TextView(this).apply {
            this.text = text
            textSize = 13f
            setPadding(0, 18, 0, 4)
        }

    private fun body(text: String): TextView =
        TextView(this).apply {
            this.text = text
            textSize = 14f
            setPadding(0, 8, 0, 8)
        }

    private fun input(hint: String): EditText =
        EditText(this).apply {
            this.hint = hint
            setSingleLine(true)
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
            )
        }

    private fun button(text: String, action: () -> Unit): Button =
        Button(this).apply {
            this.text = text
            setOnClickListener { action() }
        }

    private fun loadPrefs() {
        val prefs = Prefs.get(this)
        apiBaseInput.setText(prefs.getString(Prefs.KEY_API_BASE, ""))
        emailInput.setText(prefs.getString(Prefs.KEY_EMAIL, ""))
        phoneInput.setText(prefs.getString(Prefs.KEY_PHONE, ""))
        tokenInput.setText(prefs.getString(Prefs.KEY_AGENT_TOKEN, ""))
    }

    private fun savePrefs() {
        Prefs.get(this).edit()
            .putString(Prefs.KEY_API_BASE, apiBaseInput.text.toString().trim().trimEnd('/'))
            .putString(Prefs.KEY_EMAIL, emailInput.text.toString().trim())
            .putString(Prefs.KEY_PHONE, phoneInput.text.toString().trim())
            .putString(Prefs.KEY_AGENT_TOKEN, tokenInput.text.toString().trim())
            .apply()
        AgentLog.add(this, "Settings saved")
    }

    private fun requestNeededPermissions() {
        val permissions = mutableListOf(
            Manifest.permission.READ_CALL_LOG,
            Manifest.permission.READ_PHONE_STATE,
            Manifest.permission.SEND_SMS,
        )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissions.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        requestPermissions(permissions.toTypedArray(), 4001)
    }

    private fun registerAgent() {
        val apiBase = apiBaseInput.text.toString().trim().trimEnd('/')
        val email = emailInput.text.toString().trim()
        val password = passwordInput.text.toString()
        val phone = phoneInput.text.toString().trim()

        runInBackground("Register failed") {
            val api = AgentApi(apiBase)
            val accessToken = api.login(email, password)
            val result = api.registerAgent(accessToken, phone)
            Prefs.get(this).edit()
                .putString(Prefs.KEY_AGENT_TOKEN, result.token)
                .putString(Prefs.KEY_PHONE, result.businessPhone)
                .apply()
            runOnUiThread {
                tokenInput.setText(result.token)
                phoneInput.setText(result.businessPhone)
                AgentLog.add(this, "Registered agent ${result.agentId}")
                refreshStatus()
            }
        }
    }

    private fun startMonitoring() {
        Prefs.setMonitoringEnabled(this, true)
        val intent = Intent(this, MissedCallMonitorService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
        AgentLog.add(this, "Monitoring enabled")
        refreshStatus()
    }

    private fun stopMonitoring() {
        Prefs.setMonitoringEnabled(this, false)
        val intent = Intent(this, MissedCallMonitorService::class.java).apply {
            action = MissedCallMonitorService.ACTION_STOP
        }
        startService(intent)
        refreshStatus()
    }

    private fun heartbeatTest() {
        val apiBase = apiBaseInput.text.toString().trim().trimEnd('/')
        val token = tokenInput.text.toString().trim()
        runInBackground("Heartbeat failed") {
            AgentApi(apiBase).heartbeat(token)
            AgentLog.add(this, "Heartbeat ok")
            runOnUiThread { refreshStatus() }
        }
    }

    private fun runInBackground(errorPrefix: String, block: () -> Unit) {
        Thread {
            try {
                block()
            } catch (error: Throwable) {
                runOnUiThread {
                    AgentLog.add(this, "$errorPrefix: ${error.message}")
                    refreshStatus()
                }
            }
        }.start()
    }

    private fun refreshStatus() {
        val hasToken = tokenInput.text.toString().trim().isNotBlank()
        val hasApi = apiBaseInput.text.toString().trim().isNotBlank()
        val permissionsOk =
            checkSelfPermission(Manifest.permission.READ_CALL_LOG) == PackageManager.PERMISSION_GRANTED &&
                checkSelfPermission(Manifest.permission.SEND_SMS) == PackageManager.PERMISSION_GRANTED
        val monitoring = Prefs.isMonitoringEnabled(this)
        statusText.text = listOf(
            "API: ${if (hasApi) "set" else "missing"}",
            "Token: ${if (hasToken) "set" else "missing"}",
            "Permissions: ${if (permissionsOk) "ok" else "needed"}",
            "Monitoring: ${if (monitoring) "on" else "off"}",
        ).joinToString("\n")
        logText.text = AgentLog.text(this)
    }
}
