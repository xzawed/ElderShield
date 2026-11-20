package com.eldershield.data.remote

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

data class EnrollResult(val deviceUuid: String, val deviceToken: String)

class EnrollClient(
    private val baseUrl: String,
    private val client: OkHttpClient =
        OkHttpClient.Builder()
            .connectTimeout(20, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .build(),
) {
    fun enroll(
        integrityToken: String?,
        appVersion: String,
        model: String?,
    ): EnrollResult {
        val payload =
            JSONObject()
                .put("appVersion", appVersion)
                .put("integrityToken", integrityToken ?: JSONObject.NULL)
                .put("model", model ?: JSONObject.NULL)
        val body = payload.toString().toRequestBody(JSON_MEDIA)
        val req =
            Request.Builder()
                .url("${baseUrl.trimEnd('/')}/api/v1/devices/enroll")
                .post(body)
                .header("Content-Type", "application/json")
                .build()
        client.newCall(req).execute().use { resp ->
            val text = resp.body?.string().orEmpty()
            if (!resp.isSuccessful) {
                val detail =
                    try {
                        JSONObject(text).optString("detail", text)
                    } catch (_: Exception) {
                        text
                    }
                throw EnrollException(resp.code, detail)
            }
            val json = JSONObject(text)
            return EnrollResult(
                deviceUuid = json.getString("deviceUuid"),
                deviceToken = json.getString("deviceToken"),
            )
        }
    }

    companion object {
        private val JSON_MEDIA = "application/json; charset=utf-8".toMediaType()
    }
}

class EnrollException(val httpCode: Int, message: String) : Exception(message)
