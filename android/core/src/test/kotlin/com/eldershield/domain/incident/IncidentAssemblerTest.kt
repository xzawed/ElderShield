package com.eldershield.domain.incident

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.time.Instant

class IncidentAssemblerTest {
    private val nowMs = Instant.parse("2026-11-21T03:00:00Z").toEpochMilli()
    private val protection =
        ProtectionSnapshot(
            dnsConfigured = false,
            dnsHostClass = "none",
            callScreeningEnabled = true,
            lastRuleVersion = 2,
            protectionDegraded = true,
        )

    @Test
    fun window_filters_calls_outside_24h_plus_1h() {
        val insidePast = call(nowMs - 23L * 60 * 60 * 1000, "CN")
        val insideFuture = call(nowMs + 30L * 60 * 1000, "CN")
        val tooOld = call(nowMs - 25L * 60 * 60 * 1000, "CN")
        val tooNew = call(nowMs + 2L * 60 * 60 * 1000, "CN")
        val draft =
            IncidentAssembler.build(
                incidentId = "inc-1",
                deviceUuid = "dev-1",
                trigger = "call_reject",
                nowMs = nowMs,
                calls = listOf(tooOld, insidePast, insideFuture, tooNew),
                apps = emptyList(),
                protection = protection,
            )
        assertEquals(2, draft.calls.size)
        assertEquals(IncidentAssembler.toIso(insidePast.atEpochMs), draft.calls[0].at)
        assertEquals(IncidentAssembler.toIso(insideFuture.atEpochMs), draft.calls[1].at)
        assertEquals(IncidentAssembler.toIso(nowMs - IncidentAssembler.WINDOW_PAST_MS), draft.window.from)
        assertEquals(IncidentAssembler.toIso(nowMs + IncidentAssembler.WINDOW_FUTURE_MS), draft.window.to)
        assertEquals(IncidentAssembler.toIso(nowMs), draft.triggeredAt)
    }

    @Test
    fun triggers_is_single_item_list() {
        val draft = assemble(calls = emptyList(), trigger = "app_scan")
        assertEquals(listOf("app_scan"), draft.triggers)
        assertEquals("inc-1", draft.incidentId)
        assertEquals("dev-1", draft.deviceUuid)
    }

    @Test
    fun draft_never_includes_raw_phone_fields_or_digits() {
        val raw = "8613999887766"
        val hash = PhoneEvidenceHasher.hash(raw)
        val draft =
            assemble(
                calls =
                    listOf(
                        CallEvidenceSnapshot(
                            atEpochMs = nowMs,
                            countryIso = "CN",
                            decision = "Reject",
                            phoneHash = hash,
                            last4 = PhoneEvidenceHasher.last4(raw),
                        ),
                    ),
            )
        val names = propertyNames(draft)
        for (forbidden in listOf("phoneNumber", "number", "raw", "msisdn")) {
            assertFalse(names.any { it.equals(forbidden, ignoreCase = true) }, "found $forbidden")
        }
        assertFalse(draft.toString().contains(raw))
        assertEquals(hash, draft.calls.single().phoneHash)
        assertEquals("7766", draft.calls.single().last4)
        assertFalse(draft.calls.single().phoneHash.contains(raw))
    }

    @Test
    fun country_hints_mode_of_reject_iso_only() {
        val draft =
            assemble(
                calls =
                    listOf(
                        call(nowMs - 1000, "CN", "Reject"),
                        call(nowMs - 2000, "CN", "Reject"),
                        call(nowMs - 3000, "RU", "Reject"),
                        call(nowMs - 4000, "US", "Allow"),
                        call(nowMs - 5000, "US", "Allow"),
                    ),
            )
        assertEquals("CN", draft.countryHints.callIsoMode)
        assertNull(draft.countryHints.dnsCctldMode)
        assertEquals(CountryHints.NOTE, draft.countryHints.note)
    }

    @Test
    fun country_hints_null_when_no_reject_iso() {
        val draft =
            assemble(
                calls = listOf(call(nowMs, countryIso = null, decision = "Reject")),
            )
        assertNull(draft.countryHints.callIsoMode)
    }

    @Test
    fun dns_unavailable_nextdns_unset_when_host_not_nextdns() {
        val draft = assemble(protection = protection)
        assertFalse(draft.dns.available)
        assertEquals(IncidentAssembler.DNS_REASON_UNSET, draft.dns.unavailableReason)
        assertTrue(draft.dns.events.isEmpty())
    }

    @Test
    fun dns_unavailable_client_pending_when_nextdns_host() {
        val draft =
            assemble(
                protection = protection.copy(dnsConfigured = true, dnsHostClass = "nextdns"),
            )
        assertFalse(draft.dns.available)
        assertEquals(IncidentAssembler.DNS_REASON_PENDING, draft.dns.unavailableReason)
        assertTrue(draft.dns.events.isEmpty())
    }

    @Test
    fun apps_map_first_seen_to_iso() {
        val seen = nowMs - 60_000
        val draft =
            assemble(
                apps =
                    listOf(
                        AppForensicsSnapshot(
                            packageName = "com.example.risk",
                            signingCertSha256 = "aa",
                            apkSha256 = "bb",
                            versionName = "1.0",
                            versionCode = 3,
                            installer = null,
                            permissions = listOf("android.permission.READ_SMS"),
                            reasons = listOf("installer_null"),
                            riskScore = 80,
                            firstSeenAtEpochMs = seen,
                        ),
                    ),
            )
        val app = draft.apps.single()
        assertEquals("com.example.risk", app.packageName)
        assertEquals(IncidentAssembler.toIso(seen), app.firstSeenAt)
        assertEquals(80, app.riskScore)
        assertNull(app.installer)
    }

    private fun assemble(
        calls: List<CallEvidenceSnapshot> = emptyList(),
        apps: List<AppForensicsSnapshot> = emptyList(),
        protection: ProtectionSnapshot = this.protection,
        trigger: String = "call_reject",
    ): IncidentDraft =
        IncidentAssembler.build(
            incidentId = "inc-1",
            deviceUuid = "dev-1",
            trigger = trigger,
            nowMs = nowMs,
            calls = calls,
            apps = apps,
            protection = protection,
        )

    private fun call(
        at: Long,
        countryIso: String? = "CN",
        decision: String = "Reject",
    ): CallEvidenceSnapshot =
        CallEvidenceSnapshot(
            atEpochMs = at,
            countryIso = countryIso,
            decision = decision,
            phoneHash = "abc",
            last4 = "0000",
        )

    private fun propertyNames(value: Any?): Set<String> {
        if (value == null) return emptySet()
        if (value is String || value is Number || value is Boolean) return emptySet()
        if (value is Iterable<*>) return value.flatMap { propertyNames(it) }.toSet()
        val names = mutableSetOf<String>()
        value::class.java.declaredFields.forEach { field ->
            names += field.name
            field.isAccessible = true
            names += propertyNames(field.get(value))
        }
        return names
    }
}
