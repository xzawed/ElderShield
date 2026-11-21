package com.eldershield.domain.matching

import com.eldershield.domain.model.CountryRestriction

/**
 * Pure phone-country matching for CallScreening (UT-A-01..25).
 * Whitelist is checked by the caller before [shouldBlockCall] when CallRule is present.
 */
interface CountryRestrictionMatcher {
    fun shouldBlockCall(phoneNumber: String, rules: List<CountryRestriction>): Boolean

    fun getRestrictedCountries(rules: List<CountryRestriction>): Set<String>
}

class DefaultCountryRestrictionMatcher(
    private val callingCodeByIso: Map<String, String> = DEFAULT_CALLING_CODES,
    /** ISO alpha-2 for national (trunk-0) numbers from the device SIM region. */
    private val defaultRegionIso: String = "KR",
) : CountryRestrictionMatcher {
    override fun shouldBlockCall(phoneNumber: String, rules: List<CountryRestriction>): Boolean {
        val digits = normalizeDigits(phoneNumber, defaultRegionIso)
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

    fun matchRestrictedIso(phoneNumber: String, rules: List<CountryRestriction>): String? {
        val digits = normalizeDigits(phoneNumber, defaultRegionIso)
        if (digits.length < 8) return null
        val restricted = getRestrictedCountries(rules)
        if (restricted.isEmpty()) return null
        return matchCountryIso(digits, restricted)
    }

    fun isWhitelisted(phoneNumber: String, whitelist: List<String>): Boolean {
        val digits = normalizeDigits(phoneNumber, defaultRegionIso)
        if (digits.isEmpty()) return false
        // Exact E.164 digit match only — prefix entries like "+86" must not pass whole countries.
        return whitelist.any { entry ->
            val w = normalizeDigits(entry, defaultRegionIso)
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

        /**
         * Normalize to international digits (no '+').
         * - Strips leading '+' or '00'
         * - For [defaultRegionIso]=KR, national trunk `0…` → `82…` (010… → 8210…)
         */
        fun normalizeDigits(
            raw: String,
            defaultRegionIso: String = "KR",
        ): String {
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
            if (s.isEmpty()) return ""

            val region = defaultRegionIso.uppercase()
            if (region == "KR" && s.startsWith("0") && s.length in 9..12) {
                // National significant number after trunk 0 → prepend KR country code.
                s = "82" + s.drop(1)
            }
            return s
        }
    }
}
