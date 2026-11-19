package com.eldershield.service

import android.telecom.Call
import android.telecom.CallScreeningService
import android.util.Log
import com.eldershield.data.ActiveRuleBundleCache
import com.eldershield.data.RuleBundleJson
import com.eldershield.data.local.ElderShieldDatabase
import com.eldershield.domain.matching.CallScreeningDecision
import com.eldershield.domain.model.RuleBundle
import kotlinx.coroutines.runBlocking

/**
 * Blocks calls matching restricted countries from cached RuleBundle.
 * Whitelist from enabled CallRules wins (UT-A-20). No parent-facing notification.
 *
 * Platform note: without READ_CONTACTS, Android does not invoke this service for
 * numbers already in the address book — family KR handsets must grant that permission.
 */
class ElderCallScreeningService : CallScreeningService() {
    override fun onScreenCall(callDetails: Call.Details) {
        val number = callDetails.handle?.schemeSpecificPart.orEmpty()
        val direction = callDetails.callDirection
        val response =
            try {
                val bundle = loadCachedBundle()
                val block =
                    CallScreeningDecision.shouldBlock(
                        direction,
                        number,
                        bundle?.countryRestrictions.orEmpty(),
                        bundle?.callRules.orEmpty(),
                    )
                // Lab/diagnostics only — never log the raw number.
                Log.i(
                    TAG,
                    "onScreenCall dir=$direction len=${number.length} " +
                        "bundleVer=${bundle?.version ?: -1} block=$block",
                )
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
                Log.w(TAG, "onScreenCall fail-open")
                CallResponse.Builder().build()
            }
        respondToCall(callDetails, response)
    }

    private fun loadCachedBundle(): RuleBundle? {
        ActiveRuleBundleCache.bundle?.let { return it }
        // Cold path only — Application + RuleSyncWorker warm the cache to avoid this.
        val fromDb =
            runBlocking {
                val entity = ElderShieldDatabase.get(applicationContext).ruleBundleDao().get()
                    ?: return@runBlocking null
                RuleBundleJson.decode(entity.payloadJson)
            }
        return ActiveRuleBundleCache.publishIfNewer(fromDb)
    }

    companion object {
        private const val TAG = "ElderCallScreen"
    }
}
