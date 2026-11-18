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
        val apps = pm.getInstalledPackages(PackageManager.GET_PERMISSIONS)
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
                val flags = pkg.applicationInfo?.flags ?: 0
                val system = (flags and ApplicationInfo.FLAG_SYSTEM) != 0
                AppScanInput(
                    packageName = pkg.packageName,
                    installerPackage = installer,
                    permissions = perms,
                    isSystemApp = system,
                )
            }
        return AppRiskScorer.scoreAll(inputs, context.packageName)
    }
}
