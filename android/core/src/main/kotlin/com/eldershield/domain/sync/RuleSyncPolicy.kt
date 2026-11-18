package com.eldershield.domain.sync

import com.eldershield.domain.model.RuleBundle
import com.eldershield.domain.repository.RuleRepository

/**
 * UT-A-30..33 — version compare + cache fallback.
 * Empty cache + remote failure => no active restrictions (do not block).
 */
sealed class SyncOutcome {
    data class Updated(val bundle: RuleBundle) : SyncOutcome()

    data class Unchanged(val bundle: RuleBundle) : SyncOutcome()

    data class UsedCache(val bundle: RuleBundle) : SyncOutcome()

    /** No cache, remote failed — blocking must stay off. */
    data object EmptyNoBlock : SyncOutcome()
}

class RuleSyncPolicy(
    private val repository: RuleRepository,
) {
    suspend fun sync(): SyncOutcome {
        val cached = repository.getCachedRules()
        val remoteResult = runCatching { repository.getLatestRules() }

        if (remoteResult.isFailure) {
            return if (cached != null) {
                SyncOutcome.UsedCache(cached)
            } else {
                SyncOutcome.EmptyNoBlock
            }
        }

        val remote = remoteResult.getOrThrow()
        if (cached != null && remote.version == cached.version) {
            return SyncOutcome.Unchanged(cached)
        }
        if (cached != null && remote.version < cached.version) {
            // Prefer newer local until remote catches up; treat as unchanged cache.
            return SyncOutcome.Unchanged(cached)
        }

        repository.saveRules(remote)
        return SyncOutcome.Updated(remote)
    }

    fun activeBundle(outcome: SyncOutcome): RuleBundle? =
        when (outcome) {
            is SyncOutcome.Updated -> outcome.bundle
            is SyncOutcome.Unchanged -> outcome.bundle
            is SyncOutcome.UsedCache -> outcome.bundle
            SyncOutcome.EmptyNoBlock -> null
        }
}
