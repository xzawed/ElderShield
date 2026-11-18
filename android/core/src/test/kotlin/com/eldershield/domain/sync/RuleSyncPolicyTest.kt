package com.eldershield.domain.sync

import com.eldershield.domain.model.RuleBundle
import com.eldershield.domain.repository.RuleRepository
import kotlinx.coroutines.runBlocking
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

private class FakeRuleRepository(
    var cached: RuleBundle? = null,
    var remote: RuleBundle? = null,
    var remoteError: Throwable? = null,
) : RuleRepository {
    var saveCount: Int = 0
        private set

    override suspend fun getLatestRules(): RuleBundle {
        remoteError?.let { throw it }
        return remote ?: error("no remote")
    }

    override suspend fun getCachedRules(): RuleBundle? = cached

    override suspend fun saveRules(bundle: RuleBundle) {
        saveCount += 1
        cached = bundle
    }
}

class RuleSyncPolicyTest {
    private fun bundle(version: Int) = RuleBundle(version = version, updatedAt = "t")

    @Test
    fun `UT-A-30 remote newer version updates cache`() =
        runBlocking {
            val repo =
                FakeRuleRepository(
                    cached = bundle(1),
                    remote = bundle(2),
                )
            val outcome = RuleSyncPolicy(repo).sync()
            assertTrue(outcome is SyncOutcome.Updated)
            assertEquals(2, (outcome as SyncOutcome.Updated).bundle.version)
            assertEquals(1, repo.saveCount)
            assertEquals(2, repo.cached?.version)
        }

    @Test
    fun `UT-A-31 same version skips write`() =
        runBlocking {
            val repo =
                FakeRuleRepository(
                    cached = bundle(5),
                    remote = bundle(5),
                )
            val outcome = RuleSyncPolicy(repo).sync()
            assertTrue(outcome is SyncOutcome.Unchanged)
            assertEquals(0, repo.saveCount)
        }

    @Test
    fun `UT-A-32 remote failure returns cache without crashing`() =
        runBlocking {
            val repo =
                FakeRuleRepository(
                    cached = bundle(3),
                    remoteError = RuntimeException("network"),
                )
            val outcome = RuleSyncPolicy(repo).sync()
            assertTrue(outcome is SyncOutcome.UsedCache)
            assertEquals(3, (outcome as SyncOutcome.UsedCache).bundle.version)
            assertEquals(0, repo.saveCount)
        }

    @Test
    fun `UT-A-33 no cache and remote failure means empty no block`() =
        runBlocking {
            val repo =
                FakeRuleRepository(
                    cached = null,
                    remoteError = RuntimeException("network"),
                )
            val policy = RuleSyncPolicy(repo)
            val outcome = policy.sync()
            assertEquals(SyncOutcome.EmptyNoBlock, outcome)
            assertNull(policy.activeBundle(outcome))
        }
}
