package com.eldershield.domain.matching

import com.eldershield.domain.model.CallRule
import com.eldershield.domain.model.CountryRestriction

/** Production screening path used by CallScreeningService (UT-A-20..22). */
object CallScreeningDecision {
    private val matcher = DefaultCountryRestrictionMatcher()

    /** Android Call.Details.DIRECTION_INCOMING — keep numeric to stay JVM-testable in :core. */
    const val DIRECTION_INCOMING = 0
    const val DIRECTION_OUTGOING = 1

    fun shouldBlock(
        phoneNumber: String,
        restrictions: List<CountryRestriction>,
        callRules: List<CallRule>,
    ): Boolean = shouldBlock(DIRECTION_INCOMING, phoneNumber, restrictions, callRules)

    /**
     * SSOT §6.1: country block applies to **incoming** only.
     * Platform still invokes CallScreening for outgoing (caller-ID path); we must not reject those.
     */
    fun shouldBlock(
        callDirection: Int,
        phoneNumber: String,
        restrictions: List<CountryRestriction>,
        callRules: List<CallRule>,
    ): Boolean {
        if (callDirection != DIRECTION_INCOMING) {
            return false
        }
        val whitelist =
            callRules.filter { it.enabled }.flatMap { it.whitelist }
        if (matcher.isWhitelisted(phoneNumber, whitelist)) {
            return false
        }
        return matcher.shouldBlockCall(phoneNumber, restrictions)
    }
}
