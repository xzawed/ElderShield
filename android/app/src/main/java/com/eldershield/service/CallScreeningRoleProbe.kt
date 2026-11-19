package com.eldershield.service

import android.app.role.RoleManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
/**
 * SSOT §1.2.1 — probe call-screening role without stealing from Bitdefender peers.
 * [RoleManager.getRoleHolders] is privileged; peers are installed CallScreeningService packages.
 */
data class CallScreeningRoleStatus(
    val heldByUs: Boolean,
    /** Our package name when [heldByUs], otherwise null (do not invent Bitdefender as holder). */
    val heldBy: String?,
    /** Other packages that declare CallScreeningService (coexistence hint). */
    val peers: List<String>,
)

object CallScreeningRoleProbe {
    private const val SCREENING_ACTION = "android.telecom.CallScreeningService"

    fun probe(context: Context): CallScreeningRoleStatus {
        val self = context.packageName
        val peers = listPeerScreeners(context).filter { it != self }
        val heldByUs =
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    val rm = context.getSystemService(RoleManager::class.java)
                    rm?.isRoleHeld(RoleManager.ROLE_CALL_SCREENING) == true
                } else {
                    false
                }
            } catch (_: Exception) {
                false
            }
        return CallScreeningRoleStatus(
            heldByUs = heldByUs,
            heldBy = if (heldByUs) self else null,
            peers = peers,
        )
    }

    /** True when another CallScreening app is installed and we do not hold the role. */
    fun shouldAvoidAutoRoleRequest(context: Context): Boolean {
        val status = probe(context)
        return !status.heldByUs && status.peers.isNotEmpty()
    }

    private fun listPeerScreeners(context: Context): List<String> {
        val pm = context.packageManager
        val intent = Intent(SCREENING_ACTION)
        @Suppress("DEPRECATION")
        val resolve =
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                pm.queryIntentServices(intent, PackageManager.ResolveInfoFlags.of(0))
            } else {
                pm.queryIntentServices(intent, 0)
            }
        return resolve.mapNotNull { it.serviceInfo?.packageName }.distinct().sorted()
    }
}
