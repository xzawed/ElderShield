package com.eldershield.data

import com.eldershield.domain.model.RuleBundle

/**
 * In-memory snapshot for CallScreening — avoid Room [runBlocking] on the hot path
 * when a recent sync already warmed the cache.
 *
 * Writes are version-monotonic: a stale Room read must not overwrite a newer sync.
 */
object ActiveRuleBundleCache {
    @Volatile
    private var snapshot: RuleBundle? = null

    val bundle: RuleBundle?
        get() = snapshot

    /** Install [candidate] only if newer-or-equal to the current snapshot (null always accepts). */
    @Synchronized
    fun publishIfNewer(candidate: RuleBundle?): RuleBundle? {
        if (candidate == null) {
            return snapshot
        }
        val cur = snapshot
        if (cur == null || candidate.version >= cur.version) {
            snapshot = candidate
        }
        return snapshot
    }

    /** Test / explicit clear only. */
    @Synchronized
    fun clear() {
        snapshot = null
    }
}
