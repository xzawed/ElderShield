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

    /** Trusted Private DNS hosts (NextDNS / AdGuard). Exact or DNS subdomain only. */
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
    ): DnsStatus = fromAndroidSettings(mode.toString(), specifier, allowedHosts)

    /**
     * Accepts AOSP/Samsung string modes (`off` / `opportunistic` / `hostname`)
     * or legacy integer strings (`1` / `2` / `3`).
     */
    fun fromAndroidSettings(
        mode: String?,
        specifier: String?,
        allowedHosts: Set<String> = DEFAULT_ALLOWED_HOSTS,
    ): DnsStatus {
        val modeName =
            when (mode?.trim()?.lowercase()) {
                "1", MODE_OFF -> MODE_OFF
                "2", MODE_OPPORTUNISTIC -> MODE_OPPORTUNISTIC
                "3", MODE_PROVIDER, "provider" -> MODE_PROVIDER
                null, "" -> "unknown"
                else -> mode.trim().lowercase()
            }
        val host = specifier?.trim().orEmpty()
        val hostnameMode = modeName == MODE_PROVIDER && host.isNotEmpty()
        val trusted =
            allowedHosts.isEmpty() ||
                allowedHosts.any { allowed ->
                    host.equals(allowed, ignoreCase = true) ||
                        host.endsWith(".$allowed", ignoreCase = true)
                }
        val configured = hostnameMode && trusted
        return DnsStatus(privateDnsMode = modeName, privateDnsSpecifier = specifier, configured = configured)
    }
}
