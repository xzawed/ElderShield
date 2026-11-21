package com.eldershield.domain.incident

/** Local ring-buffer row mapped for assembly (no raw phone number). */
data class CallEvidenceSnapshot(
    val atEpochMs: Long,
    val countryIso: String?,
    val decision: String,
    val phoneHash: String,
    val last4: String?,
)

/** App forensics collected on-device before upload. */
data class AppForensicsSnapshot(
    val packageName: String,
    val signingCertSha256: String?,
    val apkSha256: String?,
    val versionName: String?,
    val versionCode: Long?,
    val installer: String?,
    val permissions: List<String>,
    val reasons: List<String>,
    val riskScore: Int,
    val firstSeenAtEpochMs: Long? = null,
)

data class ProtectionSnapshot(
    val dnsConfigured: Boolean,
    val dnsHostClass: String,
    val callScreeningEnabled: Boolean,
    val lastRuleVersion: Int,
    val protectionDegraded: Boolean,
)

data class IncidentWindow(
    val from: String,
    val to: String,
)

data class DnsEvidence(
    val available: Boolean,
    val unavailableReason: String?,
    val events: List<DnsEvidenceEvent> = emptyList(),
)

data class DnsEvidenceEvent(
    val at: String,
    val domain: String,
    val action: String,
)

data class CallEvidenceItem(
    val at: String,
    val countryIso: String?,
    val decision: String,
    val phoneHash: String,
    val last4: String?,
)

data class AppEvidenceItem(
    val packageName: String,
    val signingCertSha256: String?,
    val apkSha256: String?,
    val versionName: String?,
    val versionCode: Long?,
    val installer: String?,
    val permissions: List<String>,
    val reasons: List<String>,
    val riskScore: Int,
    val firstSeenAt: String? = null,
)

data class CountryHints(
    val callIsoMode: String?,
    val dnsCctldMode: String? = null,
    val note: String = CountryHints.NOTE,
) {
    companion object {
        const val NOTE = "추정 힌트이며 범인 소재 확정이 아님"
    }
}

/** Structured incident body matching POST /devices/incidents camelCase fields. */
data class IncidentDraft(
    val incidentId: String,
    val deviceUuid: String,
    val triggeredAt: String,
    val triggers: List<String>,
    val window: IncidentWindow,
    val apps: List<AppEvidenceItem>,
    val calls: List<CallEvidenceItem>,
    val dns: DnsEvidence,
    val countryHints: CountryHints,
    val protectionSnapshot: ProtectionSnapshot,
)
