package com.eldershield.data.remote

import com.eldershield.domain.incident.AppEvidenceItem
import com.eldershield.domain.incident.CallEvidenceItem
import com.eldershield.domain.incident.CountryHints
import com.eldershield.domain.incident.DnsEvidence
import com.eldershield.domain.incident.IncidentDraft
import com.eldershield.domain.incident.IncidentWindow
import com.eldershield.domain.incident.ProtectionSnapshot
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject

class IncidentApi(
    private val baseUrl: String,
    private val deviceApiKey: String,
    private val client: OkHttpClient = OkHttpClient(),
) {
    private val jsonMedia = "application/json; charset=utf-8".toMediaType()

    fun post(draft: IncidentDraft) {
        val body = draft.toJson().toString().toRequestBody(jsonMedia)
        val request =
            Request.Builder()
                .url(baseUrl.trimEnd('/') + "/api/v1/devices/incidents")
                .header("X-API-Key", deviceApiKey)
                .post(body)
                .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                error("/api/v1/devices/incidents HTTP ${response.code}")
            }
        }
    }

    private fun IncidentDraft.toJson(): JSONObject =
        JSONObject()
            .put("incidentId", incidentId)
            .put("deviceUuid", deviceUuid)
            .put("triggeredAt", triggeredAt)
            .put("triggers", triggers.toJsonArray())
            .put("window", window.toJson())
            .put("apps", JSONArray().also { arr -> apps.forEach { arr.put(it.toJson()) } })
            .put("calls", JSONArray().also { arr -> calls.forEach { arr.put(it.toJson()) } })
            .put("dns", dns.toJson())
            .put("countryHints", countryHints.toJson())
            .put("protectionSnapshot", protectionSnapshot.toJson())

    private fun IncidentWindow.toJson(): JSONObject =
        JSONObject().put("from", from).put("to", to)

    private fun DnsEvidence.toJson(): JSONObject {
        val events = JSONArray()
        this.events.forEach { e ->
            events.put(
                JSONObject()
                    .put("at", e.at)
                    .put("domain", e.domain)
                    .put("action", e.action),
            )
        }
        return JSONObject()
            .put("available", available)
            .putNullable("unavailableReason", unavailableReason)
            .put("events", events)
    }

    private fun CallEvidenceItem.toJson(): JSONObject =
        JSONObject()
            .put("at", at)
            .putNullable("countryIso", countryIso)
            .put("decision", decision)
            .put("phoneHash", phoneHash)
            .putNullable("last4", last4)

    private fun AppEvidenceItem.toJson(): JSONObject =
        JSONObject()
            .put("packageName", packageName)
            .putNullable("signingCertSha256", signingCertSha256)
            .putNullable("apkSha256", apkSha256)
            .putNullable("versionName", versionName)
            .putNullable("versionCode", versionCode)
            .putNullable("installer", installer)
            .put("permissions", permissions.toJsonArray())
            .put("reasons", reasons.toJsonArray())
            .put("riskScore", riskScore)
            .putNullable("firstSeenAt", firstSeenAt)

    private fun CountryHints.toJson(): JSONObject =
        JSONObject()
            .putNullable("callIsoMode", callIsoMode)
            .putNullable("dnsCctldMode", dnsCctldMode)
            .put("note", note)

    private fun ProtectionSnapshot.toJson(): JSONObject =
        JSONObject()
            .put("dnsConfigured", dnsConfigured)
            .put("dnsHostClass", dnsHostClass)
            .put("callScreeningEnabled", callScreeningEnabled)
            .put("lastRuleVersion", lastRuleVersion)
            .put("protectionDegraded", protectionDegraded)

    private fun List<String>.toJsonArray(): JSONArray {
        val arr = JSONArray()
        forEach { arr.put(it) }
        return arr
    }

    private fun JSONObject.putNullable(key: String, value: Any?): JSONObject {
        if (value == null) put(key, JSONObject.NULL) else put(key, value)
        return this
    }
}
