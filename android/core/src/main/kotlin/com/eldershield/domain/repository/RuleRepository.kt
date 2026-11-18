package com.eldershield.domain.repository

import com.eldershield.domain.model.RuleBundle

interface RuleRepository {
    suspend fun getLatestRules(): RuleBundle

    suspend fun getCachedRules(): RuleBundle?

    suspend fun saveRules(bundle: RuleBundle)
}
