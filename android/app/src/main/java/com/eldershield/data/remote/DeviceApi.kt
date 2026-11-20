package com.eldershield.data.remote

import com.eldershield.domain.scanner.AppRiskResult
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject

class DeviceApi(
    private val baseUrl: String,
    private val deviceApiKey: String,
    private val client: OkHttpClient = OkHttpClient(),
) {
    private val jsonMedia = "application/json; charset=utf-8".toMediaType()

    fun postHeartbeat(
        deviceUuid: String,
        appVersion: String,
        dnsConfigured: Boolean,
        callScreeningEnabled: Boolean,
        callScreeningHeldBy: String?,
        callScreeningPeers: List<String>,
        lastRuleVersion: Int,
        dnsHostClass: String? = null,
        lastSyncOk: Boolean = true,
        lastSyncErrorCode: String? = null,
        cachedBundleVersion: Int = 0,
        protectionDegraded: Boolean? = null,
    ) {
        val peers = JSONArray()
        callScreeningPeers.forEach { peers.put(it) }
        val body =
            JSONObject()
                .put("deviceUuid", deviceUuid)
                .put("appVersion", appVersion)
                .put("dnsConfigured", dnsConfigured)
                .put("callScreeningEnabled", callScreeningEnabled)
                .put(
                    "callScreeningHeldBy",
                    if (callScreeningHeldBy == null) JSONObject.NULL else callScreeningHeldBy,
                )
                .put("callScreeningPeers", peers)
                .put("lastRuleVersion", lastRuleVersion)
                .put("dnsHostClass", dnsHostClass ?: JSONObject.NULL)
                .put("lastSyncOk", lastSyncOk)
                .put(
                    "lastSyncErrorCode",
                    if (lastSyncErrorCode == null) JSONObject.NULL else lastSyncErrorCode,
                )
                .put("cachedBundleVersion", cachedBundleVersion)
        if (protectionDegraded != null) {
            body.put("protectionDegraded", protectionDegraded)
        }
        execute("POST", "/api/v1/devices/heartbeat", body.toString().toRequestBody(jsonMedia))
    }

    fun postHealthEvents(
        deviceUuid: String,
        events: List<Pair<String, String?>>,
    ) {
        if (events.isEmpty()) return
        val arr = JSONArray()
        events.forEach { (type, detail) ->
            val o = JSONObject().put("type", type)
            if (detail != null) o.put("detail", detail)
            arr.put(o)
        }
        val body =
            JSONObject()
                .put("deviceUuid", deviceUuid)
                .put("events", arr)
                .toString()
                .toRequestBody(jsonMedia)
        execute("POST", "/api/v1/devices/health-events", body)
    }

    fun postScanResult(
        deviceUuid: String,
        apps: List<AppRiskResult>,
    ) {
        val arr = JSONArray()
        apps.forEach { a ->
            val perms = JSONArray()
            a.dangerousPermissions.forEach { perms.put(it) }
            val reasons = JSONArray()
            a.reasons.forEach { reasons.put(it) }
            arr.put(
                JSONObject()
                    .put("packageName", a.packageName)
                    .put(
                        "installer",
                        if (a.installerPackage == null) JSONObject.NULL else a.installerPackage,
                    )
                    .put("dangerousPermissions", perms)
                    .put("riskScore", a.riskScore)
                    .put("reasons", reasons),
            )
        }
        val body =
            JSONObject()
                .put("deviceUuid", deviceUuid)
                .put("suspiciousApps", arr)
                .toString()
                .toRequestBody(jsonMedia)
        execute("POST", "/api/v1/devices/apps/scan-result", body)
    }

    private fun execute(
        method: String,
        path: String,
        body: okhttp3.RequestBody?,
    ) {
        val builder =
            Request.Builder()
                .url(baseUrl.trimEnd('/') + path)
                .header("X-API-Key", deviceApiKey)
        val request =
            when (method) {
                "POST" -> builder.post(body!!).build()
                else -> builder.get().build()
            }
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("$path HTTP ${response.code}")
        }
    }
}
