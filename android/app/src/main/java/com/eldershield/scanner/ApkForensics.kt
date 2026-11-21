package com.eldershield.scanner

import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.os.Build
import java.io.File
import java.security.MessageDigest

/** Signing cert + APK SHA-256 from PackageManager. Optional fields are null on failure. */
object ApkForensics {
    data class Result(
        val packageName: String,
        val signingCertSha256: String?,
        val apkSha256: String?,
        val versionName: String?,
        val versionCode: Long?,
        val installer: String?,
        val permissions: List<String>,
    )

    fun from(pm: PackageManager, packageName: String): Result? {
        val info = packageInfo(pm, packageName) ?: return null
        return Result(
            packageName = packageName,
            signingCertSha256 = signingCertSha256(info),
            apkSha256 = apkSha256(info),
            versionName = info.versionName,
            versionCode = versionCodeOf(info),
            installer = installerOf(pm, packageName),
            permissions = info.requestedPermissions?.toList().orEmpty(),
        )
    }

    private fun packageInfo(pm: PackageManager, packageName: String): PackageInfo? =
        try {
            val flags = PackageManager.GET_PERMISSIONS or PackageManager.GET_SIGNING_CERTIFICATES
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                pm.getPackageInfo(packageName, PackageManager.PackageInfoFlags.of(flags.toLong()))
            } else {
                @Suppress("DEPRECATION")
                pm.getPackageInfo(packageName, flags)
            }
        } catch (_: Exception) {
            null
        }

    private fun signingCertSha256(info: PackageInfo): String? =
        try {
            val bytes = signerBytes(info) ?: return null
            sha256Hex(bytes)
        } catch (_: Exception) {
            null
        }

    private fun signerBytes(info: PackageInfo): ByteArray? {
        val signingInfo = info.signingInfo
        if (signingInfo != null) {
            val signers =
                if (signingInfo.hasMultipleSigners()) {
                    signingInfo.apkContentsSigners
                } else {
                    signingInfo.signingCertificateHistory ?: signingInfo.apkContentsSigners
                }
            val first = signers?.firstOrNull()?.toByteArray()
            if (first != null) return first
        }
        @Suppress("DEPRECATION")
        return info.signatures?.firstOrNull()?.toByteArray()
    }

    private fun apkSha256(info: PackageInfo): String? {
        val path = info.applicationInfo?.sourceDir ?: return null
        return try {
            sha256File(File(path))
        } catch (_: Exception) {
            null
        }
    }

    private fun versionCodeOf(info: PackageInfo): Long? =
        try {
            info.longVersionCode
        } catch (_: Exception) {
            @Suppress("DEPRECATION")
            info.versionCode.toLong()
        }

    private fun installerOf(pm: PackageManager, packageName: String): String? =
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                pm.getInstallSourceInfo(packageName).installingPackageName
            } else {
                @Suppress("DEPRECATION")
                pm.getInstallerPackageName(packageName)
            }
        } catch (_: Exception) {
            null
        }

    private fun sha256File(file: File): String {
        val md = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buf = ByteArray(8192)
            while (true) {
                val n = input.read(buf)
                if (n <= 0) break
                md.update(buf, 0, n)
            }
        }
        return md.digest().toHex()
    }

    private fun sha256Hex(bytes: ByteArray): String =
        MessageDigest.getInstance("SHA-256").digest(bytes).toHex()

    private fun ByteArray.toHex(): String = joinToString("") { "%02x".format(it) }
}
