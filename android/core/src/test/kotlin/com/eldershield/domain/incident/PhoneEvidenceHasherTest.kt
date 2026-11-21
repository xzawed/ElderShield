package com.eldershield.domain.incident

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Test

class PhoneEvidenceHasherTest {
    @Test
    fun hash_is_stable_and_not_raw() {
        val digits = "8613999887766"
        val h = PhoneEvidenceHasher.hash(digits)
        assertEquals(64, h.length)
        assertFalse(h.contains(digits))
        assertEquals("7766", PhoneEvidenceHasher.last4(digits))
    }
}
