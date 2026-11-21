package com.eldershield.domain.incident

import java.security.MessageDigest

object PhoneEvidenceHasher {
    fun hash(normalizedDigits: String): String {
        val md = MessageDigest.getInstance("SHA-256")
        return md.digest(normalizedDigits.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
    }

    fun last4(normalizedDigits: String): String =
        normalizedDigits.takeLast(4).padStart(4, '0')
}
