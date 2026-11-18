package com.eldershield.domain.dns

/**
 * Private DNS monitor result for heartbeat (status only — no parent UI).
 */
data class DnsStatus(
    val privateDnsMode: String,
    val privateDnsSpecifier: String?,
    val configured: Boolean,
)

object DnsStatusEvaluator {
    const val MODE_OFF = "off"
    const val MODE_OPPORTUNISTIC = "opportunistic"
    const val MODE_PROVIDER = "hostname"

    fun fromAndroidSettings(
        mode: Int,
        specifier: String?,
    ): DnsStatus {
        // Settings.Global.PRIVATE_DNS_MODE_* integers commonly: 1=off, 2=opportunistic, 3=provider
        val modeName =
            when (mode) {
                1 -> MODE_OFF
                2 -> MODE_OPPORTUNISTIC
                3 -> MODE_PROVIDER
                else -> "unknown"
            }
        val configured = mode == 3 && !specifier.isNullOrBlank()
        return DnsStatus(privateDnsMode = modeName, privateDnsSpecifier = specifier, configured = configured)
    }
}
