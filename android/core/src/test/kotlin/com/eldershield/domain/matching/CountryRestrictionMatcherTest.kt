package com.eldershield.domain.matching

import com.eldershield.domain.model.CallRule
import com.eldershield.domain.model.CountryRestriction
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class CountryRestrictionMatcherTest {
    private val matcher = DefaultCountryRestrictionMatcher()

    private fun rule(
        countries: List<String>,
        applyTo: List<String> = listOf("call"),
        enabled: Boolean = true,
    ) = CountryRestriction(
        id = "r1",
        name = "test",
        countries = countries,
        applyTo = applyTo,
        enabled = enabled,
        version = 1,
    )

    @Test
    fun `UT-A-01 E164 CN is blocked`() {
        assertTrue(matcher.shouldBlockCall("+8613812345678", listOf(rule(listOf("CN")))))
    }

    @Test
    fun `UT-A-02 00 prefix CN is blocked`() {
        assertTrue(matcher.shouldBlockCall("008613812345678", listOf(rule(listOf("CN")))))
    }

    @Test
    fun `UT-A-03 digits only CN is blocked`() {
        assertTrue(matcher.shouldBlockCall("8613812345678", listOf(rule(listOf("CN")))))
    }

    @Test
    fun `UT-A-04 KR number not blocked when only CN RU`() {
        assertFalse(matcher.shouldBlockCall("+821012345678", listOf(rule(listOf("CN", "RU")))))
    }

    @Test
    fun `UT-A-05 RU is blocked`() {
        assertTrue(matcher.shouldBlockCall("+79161234567", listOf(rule(listOf("RU")))))
    }

    @Test
    fun `UT-A-06 disabled rule does not block`() {
        assertFalse(matcher.shouldBlockCall("+8613812345678", listOf(rule(listOf("CN"), enabled = false))))
    }

    @Test
    fun `UT-A-07 applyTo dns only does not block call`() {
        assertFalse(matcher.shouldBlockCall("+8613812345678", listOf(rule(listOf("CN"), applyTo = listOf("dns")))))
    }

    @Test
    fun `UT-A-08 empty number does not block`() {
        assertFalse(matcher.shouldBlockCall("", listOf(rule(listOf("CN")))))
        assertFalse(matcher.shouldBlockCall("   ", listOf(rule(listOf("CN")))))
    }

    @Test
    fun `UT-A-09 short number does not block`() {
        assertFalse(matcher.shouldBlockCall("1234", listOf(rule(listOf("CN")))))
    }

    @Test
    fun `UT-A-10 multi country group blocks each`() {
        val rules = listOf(rule(listOf("CN", "RU", "KP", "IR")))
        assertTrue(matcher.shouldBlockCall("+8613812345678", rules))
        assertTrue(matcher.shouldBlockCall("+79161234567", rules))
        assertTrue(matcher.shouldBlockCall("+850191234567", rules))
        assertTrue(matcher.shouldBlockCall("+989121234567", rules))
    }

    @Test
    fun `UT-A-11 multiple groups union`() {
        val rules = listOf(rule(listOf("CN")), rule(listOf("RU")).copy(id = "r2"))
        assertTrue(matcher.shouldBlockCall("+8613812345678", rules))
        assertTrue(matcher.shouldBlockCall("+79161234567", rules))
    }

    @Test
    fun `UT-A-12 disabled group ignored`() {
        val rules =
            listOf(
                rule(listOf("CN"), enabled = false),
                rule(listOf("RU")).copy(id = "r2"),
            )
        assertFalse(matcher.shouldBlockCall("+8613812345678", rules))
        assertTrue(matcher.shouldBlockCall("+79161234567", rules))
    }

    @Test
    fun `UT-A-13 getRestrictedCountries union`() {
        val rules =
            listOf(
                rule(listOf("CN", "RU")),
                rule(listOf("KP"), applyTo = listOf("dns")).copy(id = "r2"),
            )
        assertEquals(setOf("CN", "RU"), matcher.getRestrictedCountries(rules))
    }

    @Test
    fun `UT-A-20 whitelist wins over block country`() {
        val phone = "+8613812345678"
        assertTrue(matcher.isWhitelisted(phone, listOf("+8613812345678")))
        // screening path: whitelist first
        assertFalse(
            matcher.isWhitelisted(phone, listOf("+8613812345678")).not() &&
                matcher.shouldBlockCall(phone, listOf(rule(listOf("CN")))),
        )
        val block = !matcher.isWhitelisted(phone, listOf("+8613812345678")) &&
            matcher.shouldBlockCall(phone, listOf(rule(listOf("CN"))))
        assertFalse(block)
    }

    @Test
    fun `UT-A-21 whitelist miss still blocks`() {
        val phone = "+8613812345678"
        val block = !matcher.isWhitelisted(phone, listOf("+821011112222")) &&
            matcher.shouldBlockCall(phone, listOf(rule(listOf("CN"))))
        assertTrue(block)
    }

    @Test
    fun `UT-A-22 whitelist only no country restriction`() {
        assertFalse(matcher.shouldBlockCall("+821012345678", emptyList()))
        assertTrue(matcher.isWhitelisted("+821011112222", listOf("+821011112222")))
    }

    @Test
    fun `whitelist requires full number match not country prefix`() {
        assertFalse(matcher.isWhitelisted("+8613812345678", listOf("+86")))
        assertFalse(matcher.isWhitelisted("+8613812345678", listOf("")))
        assertFalse(matcher.isWhitelisted("+8613812345678", listOf("+")))
    }

    @Test
    fun `screening decision uses CallRule whitelist before country block`() {
        val restrictions = listOf(rule(listOf("CN")))
        val callRules =
            listOf(
                CallRule(
                    id = "cr-1",
                    countryCodes = listOf("+86"),
                    whitelist = listOf("+8613812345678"),
                    enabled = true,
                    version = 1,
                ),
            )
        assertFalse(CallScreeningDecision.shouldBlock("+8613812345678", restrictions, callRules))
        assertTrue(CallScreeningDecision.shouldBlock("+8613999999999", restrictions, callRules))
        // disabled CallRule → whitelist ignored → CN blocked
        assertTrue(
            CallScreeningDecision.shouldBlock(
                "+8613812345678",
                restrictions,
                listOf(callRules[0].copy(enabled = false)),
            ),
        )
    }

    @Test
    fun `UT-A-23 KR national 010 is blocked when KR restricted`() {
        // Device call log format on KR SIMs — trunk 0 must map to +82.
        assertTrue(matcher.shouldBlockCall("01012345678", listOf(rule(listOf("KR")))))
        assertTrue(matcher.shouldBlockCall("010-1234-5678", listOf(rule(listOf("KR")))))
    }

    @Test
    fun `UT-A-24 KR national 010 not blocked when only CN restricted`() {
        assertFalse(matcher.shouldBlockCall("01012345678", listOf(rule(listOf("CN")))))
    }

    @Test
    fun `UT-A-26 outgoing direction never country-blocks even for CN destination`() {
        val restrictions = listOf(rule(listOf("CN")))
        assertTrue(
            CallScreeningDecision.shouldBlock(
                CallScreeningDecision.DIRECTION_INCOMING,
                "+8613999999999",
                restrictions,
                emptyList(),
            ),
        )
        assertFalse(
            CallScreeningDecision.shouldBlock(
                CallScreeningDecision.DIRECTION_OUTGOING,
                "+8613999999999",
                restrictions,
                emptyList(),
            ),
        )
    }

    @Test
    fun `UT-A-25 whitelist E164 matches national KR presentation`() {
        assertTrue(matcher.isWhitelisted("01091112222", listOf("+821091112222")))
        assertFalse(
            CallScreeningDecision.shouldBlock(
                "01091112222",
                listOf(rule(listOf("KR"))),
                listOf(
                    CallRule(
                        id = "cr-wl",
                        countryCodes = emptyList(),
                        whitelist = listOf("+821091112222"),
                        enabled = true,
                        version = 1,
                    ),
                ),
            ),
        )
    }
}
