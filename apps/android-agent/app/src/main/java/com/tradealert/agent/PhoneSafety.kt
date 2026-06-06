package com.tradealert.agent

object PhoneSafety {
    fun isSafeSmsDestination(rawNumber: String): Boolean {
        val lower = rawNumber.lowercase()
        if (
            lower.isBlank() ||
            lower.contains("unknown") ||
            lower.contains("private") ||
            lower.contains("withheld") ||
            lower.contains("anonymous")
        ) {
            return false
        }

        val compact = rawNumber.replace(" ", "").replace("-", "")
        if (!Regex("^\\+?[0-9]{10,15}$").matches(compact)) {
            return false
        }

        val local = if (compact.startsWith("+44")) "0${compact.drop(3)}" else compact
        if (local == "999" || local == "112" || local == "911") {
            return false
        }

        val digitsOnly = local.filter { it.isDigit() }
        if (digitsOnly.length < 10) {
            return false
        }

        return !(
            local.startsWith("09") ||
                local.startsWith("087") ||
                compact.startsWith("+449") ||
                compact.startsWith("+4487")
            )
    }
}
