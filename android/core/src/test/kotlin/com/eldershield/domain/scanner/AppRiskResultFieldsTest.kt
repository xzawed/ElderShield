package com.eldershield.domain.scanner

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class AppRiskResultFieldsTest {
    @Test
    fun `score result carries installer and dangerous permissions for upload`() {
        val result =
            AppRiskScorer.score(
                AppScanInput(
                    packageName = "com.fake.sideload",
                    installerPackage = null,
                    permissions = listOf("android.permission.READ_SMS"),
                ),
            )
        requireNotNull(result)
        assertTrue(result.suspicious)
        assertNull(result.installerPackage)
        assertEquals(listOf("android.permission.READ_SMS"), result.dangerousPermissions)
    }
}
