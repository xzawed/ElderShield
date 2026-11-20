package com.eldershield.scanner

import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Build
import com.eldershield.domain.scanner.AppRiskResult
import com.eldershield.domain.scanner.AppRiskScorer
import com.eldershield.domain.scanner.AppScanInput

/** Collect installed apps and score risks — results go to server only (no parent UI). */
class PackageAppScanner(
    private val context: Context,
) {
    fun scanSuspicious(): List<AppRiskResult> {
        val pm = context.packageManager
        val flags = PackageManager.GET_PERMISSIONS or PackageManager.GET_SERVICES
        val apps = pm.getInstalledPackages(flags)
        val inputs =
            apps.map { pkg ->
                val installer =
                    if (Build.VERSION.SDK_INT >= 30) {
                        try {
                            pm.getInstallSourceInfo(pkg.packageName).installingPackageName
                        } catch (_: Exception) {
                            null
                        }
                    } else {
                        @Suppress("DEPRECATION")
                        pm.getInstallerPackageName(pkg.packageName)
                    }
                val perms = pkg.requestedPermissions?.toList().orEmpty()
                val flagsApp = pkg.applicationInfo?.flags ?: 0
                val system = (flagsApp and ApplicationInfo.FLAG_SYSTEM) != 0
                val overlay =
                    perms.any {
                        it == AppRiskScorer.OVERLAY_PERM ||
                            it == "SYSTEM_ALERT_WINDOW"
                    }
                val a11yService =
                    pkg.services?.any { svc ->
                        val perm = svc.permission
                        perm == "android.permission.BIND_ACCESSIBILITY_SERVICE"
                    } == true
                AppScanInput(
                    packageName = pkg.packageName,
                    installerPackage = installer,
                    permissions = perms,
                    isSystemApp = system,
                    hasOverlayPermission = overlay,
                    hasAccessibilityService = a11yService,
                )
            }
        return AppRiskScorer.scoreAll(inputs, context.packageName)
    }
}
