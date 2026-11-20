package com.eldershield.domain.scanner

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class AppRiskScorerTest {
    @Test
    fun `UT-A-40 play store no dangerous perms is not suspicious`() {
        val r =
            AppRiskScorer.score(
                AppScanInput(
                    packageName = "com.bank.app",
                    installerPackage = AppRiskScorer.PLAY_STORE,
                    permissions = emptyList(),
                ),
            )!!
        assertTrue(r.riskScore < AppRiskScorer.THRESHOLD)
        assertFalse(r.suspicious)
    }

    @Test
    fun `UT-A-41 null installer raises risk`() {
        val r =
            AppRiskScorer.score(
                AppScanInput(
                    packageName = "com.unknown.app",
                    installerPackage = null,
                    permissions = emptyList(),
                ),
            )!!
        assertTrue(r.riskScore >= 35)
    }

    @Test
    fun `UT-A-42 sideload plus READ_SMS is high suspicious`() {
        val r =
            AppRiskScorer.score(
                AppScanInput(
                    packageName = "com.fake.app",
                    installerPackage = "com.android.packageinstaller",
                    permissions = listOf("android.permission.READ_SMS", "android.permission.RECEIVE_SMS"),
                ),
            )!!
        assertTrue(r.suspicious)
        assertTrue(r.riskScore >= AppRiskScorer.THRESHOLD)
    }

    @Test
    fun `UT-A-43 accessibility bind adds high risk`() {
        val r =
            AppRiskScorer.score(
                AppScanInput(
                    packageName = "com.fake.access",
                    installerPackage = null,
                    permissions = listOf("android.permission.BIND_ACCESSIBILITY_SERVICE"),
                ),
            )!!
        assertTrue(r.suspicious)
        assertTrue(r.reasons.any { it.contains("accessibility") })
    }

    @Test
    fun overlayPermissionAddsTwentyFive() {
        val plain =
            AppRiskScorer.score(
                AppScanInput(
                    packageName = "com.overlay.app",
                    installerPackage = null,
                    permissions = emptyList(),
                ),
            )!!
        val overlay =
            AppRiskScorer.score(
                AppScanInput(
                    packageName = "com.overlay.app",
                    installerPackage = null,
                    permissions = emptyList(),
                    hasOverlayPermission = true,
                ),
            )!!
        assertEquals(plain.riskScore + 25, overlay.riskScore)
        assertTrue(overlay.reasons.contains("overlay_permission"))
    }

    @Test
    fun accessibilityServiceDeclaredAddsTwentyFive() {
        val plain =
            AppRiskScorer.score(
                AppScanInput(
                    packageName = "com.a11y.app",
                    installerPackage = AppRiskScorer.PLAY_STORE,
                    permissions = emptyList(),
                ),
            )!!
        val declared =
            AppRiskScorer.score(
                AppScanInput(
                    packageName = "com.a11y.app",
                    installerPackage = AppRiskScorer.PLAY_STORE,
                    permissions = emptyList(),
                    hasAccessibilityService = true,
                ),
            )!!
        assertEquals(25, declared.riskScore)
        assertTrue(plain.riskScore < AppRiskScorer.THRESHOLD)
        assertTrue(declared.reasons.contains("accessibility_service_declared"))
    }

    @Test
    fun `UT-A-44 system and self packages excluded`() {
        assertNull(
            AppRiskScorer.score(
                AppScanInput(
                    packageName = "com.eldershield",
                    installerPackage = null,
                    permissions = listOf("android.permission.READ_SMS"),
                ),
            ),
        )
        assertNull(
            AppRiskScorer.score(
                AppScanInput(
                    packageName = "com.android.systemui",
                    installerPackage = null,
                    permissions = listOf("android.permission.READ_SMS"),
                    isSystemApp = true,
                ),
            ),
        )
        val reported =
            AppRiskScorer.scoreAll(
                listOf(
                    AppScanInput("com.eldershield", null, listOf("android.permission.READ_SMS")),
                    AppScanInput("com.android.systemui", null, listOf("android.permission.READ_SMS"), isSystemApp = true),
                    AppScanInput(
                        "com.fake.app",
                        null,
                        listOf("android.permission.READ_SMS", "android.permission.RECEIVE_SMS"),
                    ),
                ),
            )
        assertEquals(listOf("com.fake.app"), reported.map { it.packageName })
    }

    @Test
    fun overlayPermissionRaisesScoreAndReason() {
        val r =
            AppRiskScorer.score(
                AppScanInput(
                    packageName = "com.overlay.scam",
                    installerPackage = null,
                    permissions = listOf(AppRiskScorer.OVERLAY_PERM),
                    hasOverlayPermission = true,
                ),
            )!!
        assertTrue(r.reasons.contains("overlay_permission"))
        assertTrue(r.riskScore >= 50)
        assertTrue(r.suspicious)
    }

    @Test
    fun accessibilityServiceDeclaredRaisesScore() {
        val r =
            AppRiskScorer.score(
                AppScanInput(
                    packageName = "com.a11y.scam",
                    installerPackage = "com.android.packageinstaller",
                    permissions = emptyList(),
                    hasAccessibilityService = true,
                ),
            )!!
        assertTrue(r.reasons.contains("accessibility_service_declared"))
        assertTrue(r.suspicious)
    }
}
