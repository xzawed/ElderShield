package com.eldershield.domain.scanner

data class AppScanInput(
    val packageName: String,
    val installerPackage: String?,
    val permissions: List<String>,
    val isSystemApp: Boolean = false,
    /** Other app declares SYSTEM_ALERT_WINDOW (overlay capability — P3). */
    val hasOverlayPermission: Boolean = false,
    /** Other app declares AccessibilityService (capability only; ElderShield never uses a11y). */
    val hasAccessibilityService: Boolean = false,
)

data class AppRiskResult(
    val packageName: String,
    val riskScore: Int,
    val suspicious: Boolean,
    val reasons: List<String>,
    val installerPackage: String? = null,
    val dangerousPermissions: List<String> = emptyList(),
)

object AppRiskScorer {
    const val PLAY_STORE = "com.android.vending"
    const val THRESHOLD = 50
    const val OVERLAY_PERM = "android.permission.SYSTEM_ALERT_WINDOW"

    private val dangerous =
        setOf(
            "android.permission.READ_SMS",
            "android.permission.RECEIVE_SMS",
            "android.permission.SEND_SMS",
            "android.permission.READ_CALL_LOG",
            "android.permission.BIND_ACCESSIBILITY_SERVICE",
            "android.permission.REQUEST_INSTALL_PACKAGES",
        )

    fun score(
        input: AppScanInput,
        selfPackageName: String = "com.eldershield",
    ): AppRiskResult? {
        // UT-A-44 — exclude self and system packages from reporting
        if (input.packageName == selfPackageName || input.isSystemApp) {
            return null
        }

        var score = 0
        val reasons = mutableListOf<String>()

        when {
            input.installerPackage == null -> {
                score += 35
                reasons += "installer_null"
            }
            input.installerPackage != PLAY_STORE -> {
                score += 30
                reasons += "installer_not_play_store"
            }
        }

        val normalized =
            input.permissions.map { p ->
                if (p.startsWith("android.permission.")) p else "android.permission.$p"
            }
        val dangerousHits = normalized.filter { it in dangerous }.distinct()
        score += dangerousHits.size * 20
        if (dangerousHits.isNotEmpty()) {
            reasons += "dangerous_permissions:${dangerousHits.joinToString("|")}"
        }
        // Accessibility capability bonus capped at +25 total (bind and/or declared service).
        var a11yBonus = 0
        if ("android.permission.BIND_ACCESSIBILITY_SERVICE" in dangerousHits) {
            a11yBonus = 25
            reasons += "accessibility_bind"
        }
        if (input.hasAccessibilityService) {
            if (a11yBonus == 0) {
                a11yBonus = 25
            }
            reasons += "accessibility_service_declared"
        }
        score += a11yBonus

        val overlay =
            input.hasOverlayPermission || OVERLAY_PERM in normalized
        if (overlay) {
            score += 25
            reasons += "overlay_permission"
        }

        // Play Store + no dangerous / overlay / a11y capability stays low (UT-A-40)
        if (input.installerPackage == PLAY_STORE &&
            dangerousHits.isEmpty() &&
            !overlay &&
            !input.hasAccessibilityService
        ) {
            score = minOf(score, 15)
        }

        score = score.coerceIn(0, 100)
        return AppRiskResult(
            packageName = input.packageName,
            riskScore = score,
            suspicious = score >= THRESHOLD,
            reasons = reasons,
            installerPackage = input.installerPackage,
            dangerousPermissions = dangerousHits,
        )
    }

    fun scoreAll(
        apps: List<AppScanInput>,
        selfPackageName: String = "com.eldershield",
    ): List<AppRiskResult> =
        apps.mapNotNull { score(it, selfPackageName) }.filter { it.suspicious }
}
