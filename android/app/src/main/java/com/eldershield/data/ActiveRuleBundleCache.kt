package com.eldershield.data

import com.eldershield.domain.model.RuleBundle

/**
 * In-memory snapshot for CallScreening — avoid Room [runBlocking] on the hot path
 * when a recent sync already warmed the cache.
 */
object ActiveRuleBundleCache {
    @Volatile
    var bundle: RuleBundle? = null
}
