package com.eldershield.data.remote

import com.eldershield.domain.model.CallRule
import com.eldershield.domain.model.CountryRestriction
import com.eldershield.domain.model.RuleBundle
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject

class RulesApi(
    private val baseUrl: String,
    private val deviceApiKey: String,
    private val client: OkHttpClient = OkHttpClient(),
) {
    fun fetchLatest(): RuleBundle {
        val request =
            Request.Builder()
                .url(baseUrl.trimEnd('/') + "/api/v1/rules/latest")
                .header("X-API-Key", deviceApiKey)
                .get()
                .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                error("rules/latest HTTP ${response.code}")
            }
            val body = response.body?.string() ?: error("empty body")
            return parseBundle(JSONObject(body))
        }
    }

    private fun parseBundle(json: JSONObject): RuleBundle {
        val restrictions = mutableListOf<CountryRestriction>()
        val arr: JSONArray = json.optJSONArray("countryRestrictions") ?: JSONArray()
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            restrictions +=
                CountryRestriction(
                    id = o.getString("id"),
                    name = o.getString("name"),
                    countries = o.getJSONArray("countries").toStringList(),
                    applyTo = o.getJSONArray("applyTo").toStringList(),
                    enabled = o.optBoolean("enabled", true),
                    version = o.optInt("version", 1),
                    description = if (o.isNull("description")) null else o.optString("description"),
                )
        }
        val callRules = mutableListOf<CallRule>()
        val callArr: JSONArray = json.optJSONArray("callRules") ?: JSONArray()
        for (i in 0 until callArr.length()) {
            val o = callArr.getJSONObject(i)
            callRules +=
                CallRule(
                    id = o.getString("id"),
                    countryCodes = (o.optJSONArray("countryCodes") ?: JSONArray()).toStringList(),
                    whitelist = (o.optJSONArray("whitelist") ?: JSONArray()).toStringList(),
                    enabled = o.optBoolean("enabled", true),
                    version = o.optInt("version", 1),
                )
        }
        return RuleBundle(
            version = json.optInt("version", 0),
            countryRestrictions = restrictions,
            callRules = callRules,
            updatedAt = if (json.isNull("updatedAt")) null else json.optString("updatedAt"),
        )
    }

    private fun JSONArray.toStringList(): List<String> =
        buildList {
            for (i in 0 until length()) add(getString(i))
        }
}
