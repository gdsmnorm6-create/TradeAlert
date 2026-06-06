package com.tradealert.agent

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.View
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
    private lateinit var monitoringText: TextView
    private lateinit var logText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = SURFACE
        window.navigationBarColor = SURFACE
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
        }
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
            setPadding(dp(20), dp(36), dp(20), dp(28))
            setBackgroundColor(SURFACE)
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
            )
        }

        root.addView(label("TRADEALERT", ACCENT, 12, Typeface.BOLD))
        root.addView(title("Phone agent"))
        root.addView(body("Missed calls are handled by this phone. The VPS only stores the job trail."))

        val statusCard = card()
        val statusHeader = row()
        statusHeader.addView(sectionTitle("Live status"), weightParams(1f))
        statusHeader.addView(pill("Android SIM"))
        statusCard.addView(statusHeader)
        statusText = body("")
        monitoringText = label("", TEXT, 20, Typeface.BOLD)
        statusCard.addView(monitoringText)
        statusCard.addView(statusText)
        root.addView(statusCard)

        val controls = card()
        controls.addView(sectionTitle("Monitoring"))
        controls.addView(body("Keep this on while you are working. Pause it when you do not want auto replies."))
        controls.addView(buttonRow(
            primaryButton("Start monitoring") {
                savePrefs()
                startMonitoring()
            },
            dangerButton("Stop") {
                stopMonitoring()
            },
        ))
        controls.addView(buttonRow(
            secondaryButton("Permissions") {
                requestNeededPermissions()
            },
            secondaryButton("Heartbeat") {
                savePrefs()
                heartbeatTest()
            },
        ))
        root.addView(controls)

        val setup = card()
        setup.addView(sectionTitle("Setup"))
        apiBaseInput = input("http://100.x.x.x:8000")
        emailInput = input("ian@tradealert.demo")
        passwordInput = input("TradeAlert password").apply {
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
        }
        phoneInput = input("07432870739")
        tokenInput = input("Created after registration").apply {
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
        }
        setup.addView(field("API URL", apiBaseInput))
        setup.addView(field("Email", emailInput))
        setup.addView(field("Password", passwordInput))
        setup.addView(field("Phone/SIM number", phoneInput))
        setup.addView(field("Agent token", tokenInput))
        setup.addView(buttonRow(
            secondaryButton("Save") {
                savePrefs()
                refreshStatus()
            },
            primaryButton("Register phone") {
                savePrefs()
                registerAgent()
            },
        ))
        root.addView(setup)

        val logCard = card()
        val logHeader = row()
        logHeader.addView(sectionTitle("Recent log"), weightParams(1f))
        logHeader.addView(textButton("Refresh") { refreshStatus() })
        logCard.addView(logHeader)
        logText = body("")
        logCard.addView(logText)
        root.addView(logCard)

        setContentView(ScrollView(this).apply {
            setBackgroundColor(SURFACE)
            addView(root)
        })
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
        monitoringText.text = if (monitoring) "Auto replies are on" else "Auto replies are paused"
        monitoringText.setTextColor(if (monitoring) ACCENT else WARNING)
        statusText.text = listOf(
            "API ${if (hasApi) "connected" else "missing"}",
            "Token ${if (hasToken) "stored" else "missing"}",
            "Permissions ${if (permissionsOk) "ready" else "needed"}",
        ).joinToString("  |  ")
        logText.text = AgentLog.text(this).ifBlank { "No activity yet." }
    }

    private fun card(): LinearLayout =
        LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(16), dp(16), dp(16))
            background = roundRect(CARD, dp(14), STROKE)
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
            ).apply {
                topMargin = dp(14)
            }
        }

    private fun row(): LinearLayout =
        LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }

    private fun buttonRow(left: Button, right: Button): LinearLayout =
        row().apply {
            addView(left, weightParams(1f))
            addView(right, weightParams(1f).apply { leftMargin = dp(10) })
            setPadding(0, dp(10), 0, 0)
        }

    private fun field(label: String, input: EditText): LinearLayout =
        LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, dp(10), 0, 0)
            addView(label(label, MUTED, 12, Typeface.BOLD))
            addView(input)
        }

    private fun input(hint: String): EditText =
        EditText(this).apply {
            this.hint = hint
            setSingleLine(true)
            textSize = 15f
            setTextColor(TEXT)
            setHintTextColor(MUTED)
            setPadding(dp(12), 0, dp(12), 0)
            background = roundRect(Color.WHITE, dp(10), STROKE)
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(46),
            ).apply {
                topMargin = dp(6)
            }
        }

    private fun primaryButton(text: String, action: () -> Unit): Button =
        styledButton(text, ACCENT, Color.WHITE, action)

    private fun secondaryButton(text: String, action: () -> Unit): Button =
        styledButton(text, Color.WHITE, TEXT, action, STROKE)

    private fun dangerButton(text: String, action: () -> Unit): Button =
        styledButton(text, DANGER_SURFACE, DANGER, action, DANGER)

    private fun styledButton(
        text: String,
        backgroundColor: Int,
        textColor: Int,
        action: () -> Unit,
        strokeColor: Int = backgroundColor,
    ): Button =
        Button(this).apply {
            this.text = text
            isAllCaps = false
            textSize = 14f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(textColor)
            background = roundRect(backgroundColor, dp(12), strokeColor)
            minHeight = 0
            minimumHeight = 0
            setPadding(dp(10), 0, dp(10), 0)
            setOnClickListener { action() }
        }

    private fun textButton(text: String, action: () -> Unit): TextView =
        label(text, ACCENT, 13, Typeface.BOLD).apply {
            setPadding(dp(10), dp(6), dp(10), dp(6))
            setOnClickListener { action() }
        }

    private fun pill(text: String): TextView =
        label(text, ACCENT, 12, Typeface.BOLD).apply {
            background = roundRect(ACCENT_SOFT, dp(999), ACCENT_SOFT)
            setPadding(dp(10), dp(6), dp(10), dp(6))
        }

    private fun title(text: String): TextView =
        label(text, TEXT, 30, Typeface.BOLD).apply {
            setPadding(0, dp(2), 0, dp(6))
        }

    private fun sectionTitle(text: String): TextView =
        label(text, TEXT, 18, Typeface.BOLD)

    private fun body(text: String): TextView =
        label(text, MUTED, 14, Typeface.NORMAL).apply {
            setLineSpacing(dp(2).toFloat(), 1f)
            setPadding(0, dp(8), 0, 0)
        }

    private fun label(text: String, color: Int, size: Int, style: Int): TextView =
        TextView(this).apply {
            this.text = text
            textSize = size.toFloat()
            setTextColor(color)
            typeface = Typeface.create(Typeface.DEFAULT, style)
        }

    private fun weightParams(weight: Float): LinearLayout.LayoutParams =
        LinearLayout.LayoutParams(0, dp(46), weight)

    private fun roundRect(fill: Int, radius: Int, stroke: Int): GradientDrawable =
        GradientDrawable().apply {
            setColor(fill)
            cornerRadius = radius.toFloat()
            setStroke(dp(1), stroke)
        }

    private fun dp(value: Int): Int =
        (value * resources.displayMetrics.density).toInt()

    companion object {
        private val SURFACE = Color.rgb(246, 244, 239)
        private val CARD = Color.rgb(255, 255, 255)
        private val TEXT = Color.rgb(28, 35, 38)
        private val MUTED = Color.rgb(96, 106, 111)
        private val STROKE = Color.rgb(224, 222, 214)
        private val ACCENT = Color.rgb(15, 118, 110)
        private val ACCENT_SOFT = Color.rgb(224, 244, 241)
        private val WARNING = Color.rgb(154, 92, 17)
        private val DANGER = Color.rgb(172, 48, 48)
        private val DANGER_SURFACE = Color.rgb(255, 237, 237)
    }
}
