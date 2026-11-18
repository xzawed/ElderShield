package com.eldershield.service

import android.telecom.Call
import android.telecom.CallScreeningService
import com.eldershield.data.local.ElderShieldDatabase
import com.eldershield.domain.matching.DefaultCountryRestrictionMatcher
import com.eldershield.domain.model.CountryRestriction
import com.eldershield.domain.model.RuleBundle
import kotlinx.coroutines.runBlocking
import org.json.JSONArray
import org.json.JSONObject

/**
 * Blocks calls matching restricted countries from cached RuleBundle.
 * No parent-facing notification (hard constraint).
 */
class ElderCallScreeningService : CallScreeningService() {
    private val matcher = DefaultCountryRestrictionMatcher()

    override fun onScreenCall(callDetails: Call.Details) {
        val number = callDetails.handle?.schemeSpecificPart.orEmpty()
        val response =
            try {
                val bundle = loadCachedBundle()
                val whitelist = emptyList<String>() // CallRule whitelist wired in later slice
                val block =
                    if (matcher.isWhitelisted(number, whitelist)) {
                        false
                    } else {
                        matcher.shouldBlockCall(number, bundle?.countryRestrictions.orEmpty())
                    }
                if (block) {
                    CallResponse.Builder()
                        .setDisallowCall(true)
                        .setRejectCall(true)
                        .setSkipCallLog(false)
                        .setSkipNotification(true)
                        .build()
                } else {
                    CallResponse.Builder().build()
                }
            } catch (_: Exception) {
                // Fail open — do not crash call flow (aligns with EmptyNoBlock posture).
                CallResponse.Builder().build()
            }
        respondToCall(callDetails, response)
    }

    private fun loadCachedBundle(): RuleBundle? =
        runBlocking {
            val entity = ElderShieldDatabase.get(applicationContext).ruleBundleDao().get() ?: return@runBlocking null
            decode(entity.payloadJson)
        }

    private fun decode(json: String): RuleBundle {
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
        return RuleBundle(
            version = root.optInt("version", 0),
            countryRestrictions = list,
            updatedAt = if (root.isNull("updatedAt")) null else root.optString("updatedAt"),
        )
    }
}
