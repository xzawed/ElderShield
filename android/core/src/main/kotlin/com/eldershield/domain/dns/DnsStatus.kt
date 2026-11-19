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

    /** Trusted Private DNS host fragments (NextDNS / AdGuard). */
    val DEFAULT_ALLOWED_HOSTS: Set<String> =
        setOf(
            "dns.adguard.com",
            "dns-unfiltered.adguard.com",
            "dns.nextdns.io",
            "nextdns.io",
        )

    fun fromAndroidSettings(
        mode: Int,
        specifier: String?,
        allowedHosts: Set<String> = DEFAULT_ALLOWED_HOSTS,
    ): DnsStatus {
        // Settings.Global.PRIVATE_DNS_MODE_* integers commonly: 1=off, 2=opportunistic, 3=provider
        val modeName =
            when (mode) {
                1 -> MODE_OFF
                2 -> MODE_OPPORTUNISTIC
                3 -> MODE_PROVIDER
                else -> "unknown"
            }
        val host = specifier?.trim().orEmpty()
        val hostnameMode = mode == 3 && host.isNotEmpty()
        val trusted =
            allowedHosts.isEmpty() ||
                allowedHosts.any { allowed ->
                    host.equals(allowed, ignoreCase = true) ||
                        host.endsWith(".$allowed", ignoreCase = true) ||
                        host.contains(allowed, ignoreCase = true)
                }
        val configured = hostnameMode && trusted
        return DnsStatus(privateDnsMode = modeName, privateDnsSpecifier = specifier, configured = configured)
    }
}
