package com.eldershield.domain.dns

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class DnsStatusEvaluatorTest {
    @Test
    fun providerHostnameMeansConfigured() {
        val s = DnsStatusEvaluator.fromAndroidSettings(3, "dns.adguard.com")
        assertTrue(s.configured)
        assertEquals(DnsStatusEvaluator.MODE_PROVIDER, s.privateDnsMode)
    }

    @Test
    fun offOrOpportunisticNotConfigured() {
        assertFalse(DnsStatusEvaluator.fromAndroidSettings(1, null).configured)
        assertFalse(DnsStatusEvaluator.fromAndroidSettings(2, null).configured)
        assertFalse(DnsStatusEvaluator.fromAndroidSettings(3, "").configured)
    }
}
