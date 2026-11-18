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
        lastRuleVersion: Int,
    ) {
        val body =
            JSONObject()
                .put("deviceUuid", deviceUuid)
                .put("appVersion", appVersion)
                .put("dnsConfigured", dnsConfigured)
                .put("callScreeningEnabled", callScreeningEnabled)
                .put("lastRuleVersion", lastRuleVersion)
                .toString()
                .toRequestBody(jsonMedia)
        execute("POST", "/api/v1/devices/heartbeat", body)
    }

    fun postScanResult(
        deviceUuid: String,
        apps: List<AppRiskResult>,
    ) {
        val arr = JSONArray()
        apps.forEach { a ->
            arr.put(
                JSONObject()
                    .put("packageName", a.packageName)
                    .put("installer", JSONObject.NULL)
                    .put("dangerousPermissions", JSONArray())
                    .put("riskScore", a.riskScore),
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
