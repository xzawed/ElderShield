package com.eldershield.domain.sync

import com.eldershield.domain.model.RuleBundle
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class SyncWorkDispositionTest {
    @Test
    fun `remote success outcomes do not need retry`() {
        val b = RuleBundle(version = 1)
        assertFalse(SyncWorkDisposition.shouldRetry(SyncOutcome.Updated(b)))
        assertFalse(SyncWorkDisposition.shouldRetry(SyncOutcome.Unchanged(b)))
    }

    @Test
    fun `remote failure outcomes should retry while keeping fail-open policy`() {
        val b = RuleBundle(version = 2)
        assertTrue(SyncWorkDisposition.shouldRetry(SyncOutcome.UsedCache(b)))
        assertTrue(SyncWorkDisposition.shouldRetry(SyncOutcome.EmptyNoBlock))
    }
}
