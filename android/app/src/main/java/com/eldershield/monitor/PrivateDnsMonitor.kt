package com.eldershield.monitor

import android.content.Context
import android.provider.Settings
import com.eldershield.domain.dns.DnsStatus
import com.eldershield.domain.dns.DnsStatusEvaluator

class PrivateDnsMonitor(
    private val context: Context,
) {
    fun read(): DnsStatus {
        val resolver = context.contentResolver
        // AOSP/Samsung store PRIVATE_DNS_MODE as a string (off/opportunistic/hostname).
        val modeString = Settings.Global.getString(resolver, "private_dns_mode")
        val mode =
            modeString
                ?: runCatching {
                    Settings.Global.getInt(resolver, "private_dns_mode", 1).toString()
                }.getOrDefault("1")
        val specifier = Settings.Global.getString(resolver, "private_dns_specifier")
        return DnsStatusEvaluator.fromAndroidSettings(mode, specifier)
    }
}
