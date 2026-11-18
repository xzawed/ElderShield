package com.eldershield.data

import com.eldershield.data.local.RuleBundleDao
import com.eldershield.data.local.RuleBundleEntity
import com.eldershield.data.remote.RulesApi
import com.eldershield.domain.model.CountryRestriction
import com.eldershield.domain.model.RuleBundle
import com.eldershield.domain.repository.RuleRepository
import org.json.JSONArray
import org.json.JSONObject

class RuleRepositoryImpl(
    private val dao: RuleBundleDao,
    private val api: RulesApi,
) : RuleRepository {
    override suspend fun getLatestRules(): RuleBundle = api.fetchLatest()

    override suspend fun getCachedRules(): RuleBundle? {
        val entity = dao.get() ?: return null
        return decode(entity.payloadJson)
    }

    override suspend fun saveRules(bundle: RuleBundle) {
        dao.upsert(
            RuleBundleEntity(
                version = bundle.version,
                payloadJson = encode(bundle),
                updatedAt = bundle.updatedAt,
            ),
        )
    }

    private fun encode(bundle: RuleBundle): String {
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
        return JSONObject()
            .put("version", bundle.version)
            .put("countryRestrictions", restrictions)
            .put("updatedAt", bundle.updatedAt)
            .toString()
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
