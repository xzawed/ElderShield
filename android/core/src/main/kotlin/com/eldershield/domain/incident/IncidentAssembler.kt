package com.eldershield.domain.incident

import java.time.Instant

object IncidentAssembler {
    const val WINDOW_PAST_MS = 24L * 60L * 60L * 1000L
    const val WINDOW_FUTURE_MS = 60L * 60L * 1000L
    const val DNS_REASON_UNSET = "nextdns_unset"
    const val DNS_REASON_PENDING = "client_pending"
    const val DECISION_REJECT = "Reject"
    const val HOST_NEXTDNS = "nextdns"

    fun build(
        incidentId: String,
        deviceUuid: String,
        trigger: String,
        nowMs: Long,
        calls: List<CallEvidenceSnapshot>,
        apps: List<AppForensicsSnapshot>,
        protection: ProtectionSnapshot,
    ): IncidentDraft {
        val fromMs = nowMs - WINDOW_PAST_MS
        val toMs = nowMs + WINDOW_FUTURE_MS
        val inWindow =
            calls.filter { it.atEpochMs in fromMs..toMs }
                .sortedBy { it.atEpochMs }
        return IncidentDraft(
            incidentId = incidentId,
            deviceUuid = deviceUuid,
            triggeredAt = toIso(nowMs),
            triggers = listOf(trigger),
            window = IncidentWindow(from = toIso(fromMs), to = toIso(toMs)),
            apps = apps.map { toAppItem(it) },
            calls = inWindow.map { toCallItem(it) },
            dns = DnsEvidence(
                available = false,
                unavailableReason = dnsUnavailableReason(protection.dnsHostClass),
                events = emptyList(),
            ),
            countryHints = CountryHints(
                callIsoMode = rejectCountryIsoMode(inWindow),
                dnsCctldMode = null,
            ),
            protectionSnapshot = protection,
        )
    }

    internal fun toIso(epochMs: Long): String = Instant.ofEpochMilli(epochMs).toString()

    private fun toCallItem(call: CallEvidenceSnapshot): CallEvidenceItem =
        CallEvidenceItem(
            at = toIso(call.atEpochMs),
            countryIso = call.countryIso,
            decision = call.decision,
            phoneHash = call.phoneHash,
            last4 = call.last4,
        )

    private fun toAppItem(app: AppForensicsSnapshot): AppEvidenceItem =
        AppEvidenceItem(
            packageName = app.packageName,
            signingCertSha256 = app.signingCertSha256,
            apkSha256 = app.apkSha256,
            versionName = app.versionName,
            versionCode = app.versionCode,
            installer = app.installer,
            permissions = app.permissions,
            reasons = app.reasons,
            riskScore = app.riskScore,
            firstSeenAt = app.firstSeenAtEpochMs?.let { toIso(it) },
        )

    private fun dnsUnavailableReason(hostClass: String): String =
        if (hostClass.equals(HOST_NEXTDNS, ignoreCase = true)) {
            DNS_REASON_PENDING
        } else {
            DNS_REASON_UNSET
        }

    /** Mode (most frequent) ISO among Rejected calls; ties broken lexicographically. */
    private fun rejectCountryIsoMode(calls: List<CallEvidenceSnapshot>): String? {
        val isos =
            calls
                .filter { it.decision.equals(DECISION_REJECT, ignoreCase = true) }
                .mapNotNull { iso -> iso.countryIso?.trim()?.takeIf { it.isNotEmpty() } }
                .map { it.uppercase() }
        if (isos.isEmpty()) return null
        val counts = isos.groupingBy { it }.eachCount()
        val max = counts.values.maxOrNull() ?: return null
        return counts.filterValues { it == max }.keys.sorted().first()
    }
}
