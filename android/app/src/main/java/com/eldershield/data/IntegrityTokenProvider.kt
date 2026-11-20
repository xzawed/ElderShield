package com.eldershield.data

import android.content.Context
import com.eldershield.BuildConfig
import com.google.android.play.core.integrity.IntegrityManagerFactory
import com.google.android.play.core.integrity.IntegrityTokenRequest
import kotlinx.coroutines.suspendCancellableCoroutine
import java.security.SecureRandom
import java.util.Base64
import kotlin.coroutines.resume

/**
 * Requests a Play Integrity token for enroll.
 * Returns null when cloud project is unset (lab) or Play services fail — server then
 * accepts only if ELDERSHIELD_ENROLL_SKIP_INTEGRITY=1.
 */
object IntegrityTokenProvider {
    suspend fun requestOrNull(context: Context): String? {
        val projectNumber = BuildConfig.PLAY_CLOUD_PROJECT_NUMBER.trim()
        if (projectNumber.isEmpty() || projectNumber == "0") {
            return null
        }
        val number =
            try {
                projectNumber.toLong()
            } catch (_: NumberFormatException) {
                return null
            }
        val nonce = newNonce()
        return suspendCancellableCoroutine { cont ->
            val manager = IntegrityManagerFactory.create(context.applicationContext)
            val request =
                IntegrityTokenRequest.builder()
                    .setNonce(nonce)
                    .setCloudProjectNumber(number)
                    .build()
            manager
                .requestIntegrityToken(request)
                .addOnSuccessListener { response ->
                    if (cont.isActive) cont.resume(response.token())
                }.addOnFailureListener {
                    if (cont.isActive) cont.resume(null)
                }
        }
    }

    private fun newNonce(): String {
        val bytes = ByteArray(24)
        SecureRandom().nextBytes(bytes)
        return if (android.os.Build.VERSION.SDK_INT >= 26) {
            Base64.getUrlEncoder().withoutPadding().encodeToString(bytes)
        } else {
            android.util.Base64.encodeToString(
                bytes,
                android.util.Base64.URL_SAFE or android.util.Base64.NO_WRAP or android.util.Base64.NO_PADDING,
            )
        }
    }
}
