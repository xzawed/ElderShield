package com.eldershield.domain.matching

import com.eldershield.domain.model.CountryRestriction

/**
 * Pure phone-country matching for CallScreening (UT-A-01..22).
 * Whitelist is checked by the caller before [shouldBlockCall] when CallRule is present.
 */
interface CountryRestrictionMatcher {
    fun shouldBlockCall(phoneNumber: String, rules: List<CountryRestriction>): Boolean

    fun getRestrictedCountries(rules: List<CountryRestriction>): Set<String>
}

class DefaultCountryRestrictionMatcher(
    private val callingCodeByIso: Map<String, String> = DEFAULT_CALLING_CODES,
) : CountryRestrictionMatcher {
    override fun shouldBlockCall(phoneNumber: String, rules: List<CountryRestriction>): Boolean {
        val digits = normalizeDigits(phoneNumber)
        if (digits.length < 8) return false

        val active =
            rules.filter { it.enabled && it.applyTo.any { a -> a.equals("call", ignoreCase = true) } }
        if (active.isEmpty()) return false

        val restricted = getRestrictedCountries(active)
        if (restricted.isEmpty()) return false

        val matchedIso = matchCountryIso(digits, restricted) ?: return false
        return matchedIso in restricted
    }

    override fun getRestrictedCountries(rules: List<CountryRestriction>): Set<String> =
        rules
            .filter { it.enabled && it.applyTo.any { a -> a.equals("call", ignoreCase = true) } }
            .flatMap { it.countries.map { c -> c.uppercase() } }
            .toSet()

    fun isWhitelisted(phoneNumber: String, whitelist: List<String>): Boolean {
        val digits = normalizeDigits(phoneNumber)
        if (digits.isEmpty()) return false
        // Exact E.164 digit match only — prefix entries like "+86" must not pass whole countries.
        return whitelist.any { entry ->
            val w = normalizeDigits(entry)
            w.isNotEmpty() && w == digits
        }
    }

    private fun matchCountryIso(digits: String, restrictedIso: Set<String>): String? {
        val candidates =
            restrictedIso.mapNotNull { iso ->
                val code = callingCodeByIso[iso] ?: return@mapNotNull null
                code.removePrefix("+") to iso
            }.sortedByDescending { it.first.length }

        for ((code, iso) in candidates) {
            if (digits.startsWith(code)) return iso
        }
        return null
    }

    companion object {
        val DEFAULT_CALLING_CODES: Map<String, String> =
            mapOf(
                "CN" to "+86",
                "RU" to "+7",
                "KP" to "+850",
                "IR" to "+98",
                "KR" to "+82",
                "US" to "+1",
                "JP" to "+81",
            )

        fun normalizeDigits(raw: String): String {
            val trimmed = raw.trim()
            if (trimmed.isEmpty()) return ""
            var s = trimmed.filter { it.isDigit() || it == '+' }
            if (s.startsWith("+")) {
                s = s.drop(1).filter { it.isDigit() }
            } else if (s.startsWith("00")) {
                s = s.drop(2).filter { it.isDigit() }
            } else {
                s = s.filter { it.isDigit() }
            }
            return s
        }
    }
}
