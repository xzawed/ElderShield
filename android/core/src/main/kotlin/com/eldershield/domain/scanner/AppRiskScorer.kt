package com.eldershield.domain.scanner

data class AppScanInput(
    val packageName: String,
    val installerPackage: String?,
    val permissions: List<String>,
    val isSystemApp: Boolean = false,
)

data class AppRiskResult(
    val packageName: String,
    val riskScore: Int,
    val suspicious: Boolean,
    val reasons: List<String>,
)

object AppRiskScorer {
    const val PLAY_STORE = "com.android.vending"
    const val THRESHOLD = 50

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
        if ("android.permission.BIND_ACCESSIBILITY_SERVICE" in dangerousHits) {
            score += 25
            reasons += "accessibility_bind"
        }

        // Play Store + no dangerous perms stays low (UT-A-40)
        if (input.installerPackage == PLAY_STORE && dangerousHits.isEmpty()) {
            score = minOf(score, 15)
        }

        score = score.coerceIn(0, 100)
        return AppRiskResult(
            packageName = input.packageName,
            riskScore = score,
            suspicious = score >= THRESHOLD,
            reasons = reasons,
        )
    }

    fun scoreAll(
        apps: List<AppScanInput>,
        selfPackageName: String = "com.eldershield",
    ): List<AppRiskResult> =
        apps.mapNotNull { score(it, selfPackageName) }.filter { it.suspicious }
}
