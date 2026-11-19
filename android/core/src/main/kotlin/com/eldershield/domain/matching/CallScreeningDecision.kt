package com.eldershield.domain.matching

import com.eldershield.domain.model.CallRule
import com.eldershield.domain.model.CountryRestriction

/** Production screening path used by CallScreeningService (UT-A-20..22). */
object CallScreeningDecision {
    private val matcher = DefaultCountryRestrictionMatcher()

    fun shouldBlock(
        phoneNumber: String,
        restrictions: List<CountryRestriction>,
        callRules: List<CallRule>,
    ): Boolean {
        val whitelist =
            callRules.filter { it.enabled }.flatMap { it.whitelist }
        if (matcher.isWhitelisted(phoneNumber, whitelist)) {
            return false
        }
        return matcher.shouldBlockCall(phoneNumber, restrictions)
    }
}
