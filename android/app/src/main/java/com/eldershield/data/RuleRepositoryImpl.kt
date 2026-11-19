package com.eldershield.data

import com.eldershield.data.local.RuleBundleDao
import com.eldershield.data.local.RuleBundleEntity
import com.eldershield.data.remote.RulesApi
import com.eldershield.domain.model.RuleBundle
import com.eldershield.domain.repository.RuleRepository

class RuleRepositoryImpl(
    private val dao: RuleBundleDao,
    private val api: RulesApi,
) : RuleRepository {
    override suspend fun getLatestRules(): RuleBundle = api.fetchLatest()

    override suspend fun getCachedRules(): RuleBundle? {
        val entity = dao.get() ?: return null
        return RuleBundleJson.decode(entity.payloadJson)
    }

    override suspend fun saveRules(bundle: RuleBundle) {
        dao.upsert(
            RuleBundleEntity(
                version = bundle.version,
                payloadJson = RuleBundleJson.encode(bundle),
                updatedAt = bundle.updatedAt,
            ),
        )
    }
}
