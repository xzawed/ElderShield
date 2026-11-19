package com.eldershield.data

import com.eldershield.domain.model.CallRule
import com.eldershield.domain.model.CountryRestriction
import com.eldershield.domain.model.RuleBundle
import org.json.JSONArray
import org.json.JSONObject

/** Single decode/encode path for Room cache + CallScreening (avoid drift). */
object RuleBundleJson {
    fun decode(json: String): RuleBundle {
        val root = JSONObject(json)
        val arr = root.optJSONArray("countryRestrictions") ?: JSONArray()
        val list = mutableListOf<CountryRestriction>()
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val countries = o.getJSONArray("countries")
            val applyTo = o.getJSONArray("applyTo")
            list +=
                CountryRestriction(
                    id = o.getString("id"),
                    name = o.getString("name"),
                    countries = (0 until countries.length()).map { countries.getString(it) },
                    applyTo = (0 until applyTo.length()).map { applyTo.getString(it) },
                    enabled = o.optBoolean("enabled", true),
                    version = o.optInt("version", 1),
                    description = if (o.isNull("description")) null else o.optString("description"),
                )
        }
        val callRules = mutableListOf<CallRule>()
        val callArr = root.optJSONArray("callRules") ?: JSONArray()
        for (i in 0 until callArr.length()) {
            val o = callArr.getJSONObject(i)
            val codes = o.optJSONArray("countryCodes") ?: JSONArray()
            val wl = o.optJSONArray("whitelist") ?: JSONArray()
            callRules +=
                CallRule(
                    id = o.getString("id"),
                    countryCodes = (0 until codes.length()).map { codes.getString(it) },
                    whitelist = (0 until wl.length()).map { wl.getString(it) },
                    enabled = o.optBoolean("enabled", true),
                    version = o.optInt("version", 1),
                )
        }
        return RuleBundle(
            version = root.optInt("version", 0),
            countryRestrictions = list,
            callRules = callRules,
            updatedAt = if (root.isNull("updatedAt")) null else root.optString("updatedAt"),
        )
    }

    fun encode(bundle: RuleBundle): String {
        val restrictions = JSONArray()
        bundle.countryRestrictions.forEach { r ->
            restrictions.put(
                JSONObject()
                    .put("id", r.id)
                    .put("name", r.name)
                    .put("countries", JSONArray(r.countries))
                    .put("applyTo", JSONArray(r.applyTo))
                    .put("enabled", r.enabled)
                    .put("version", r.version)
                    .put("description", r.description),
            )
        }
        val callRules = JSONArray()
        bundle.callRules.forEach { c ->
            callRules.put(
                JSONObject()
                    .put("id", c.id)
                    .put("countryCodes", JSONArray(c.countryCodes))
                    .put("whitelist", JSONArray(c.whitelist))
                    .put("enabled", c.enabled)
                    .put("version", c.version),
            )
        }
        return JSONObject()
            .put("version", bundle.version)
            .put("countryRestrictions", restrictions)
            .put("callRules", callRules)
            .put("updatedAt", bundle.updatedAt)
            .toString()
    }
}
