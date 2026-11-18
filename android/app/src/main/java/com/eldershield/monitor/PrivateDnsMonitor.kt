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
        val mode =
            Settings.Global.getInt(
                resolver,
                "private_dns_mode",
                1,
            )
        val specifier = Settings.Global.getString(resolver, "private_dns_specifier")
        return DnsStatusEvaluator.fromAndroidSettings(mode, specifier)
    }
}
