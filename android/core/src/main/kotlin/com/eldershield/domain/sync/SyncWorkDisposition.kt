package com.eldershield.domain.sync

/**
 * Maps sync outcome to WorkManager retry policy.
 * Cache / EmptyNoBlock still apply for call screening (fail-open), but the worker
 * must retry so a transient outage is not treated as a successful period.
 */
object SyncWorkDisposition {
    fun shouldRetry(outcome: SyncOutcome): Boolean =
        when (outcome) {
            is SyncOutcome.UsedCache,
            SyncOutcome.EmptyNoBlock,
            -> true
            is SyncOutcome.Updated,
            is SyncOutcome.Unchanged,
            -> false
        }
}
