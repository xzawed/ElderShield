package com.eldershield.data

import android.content.Context
import com.eldershield.BuildConfig
import com.google.android.play.core.integrity.IntegrityManagerFactory
import com.google.android.play.core.integrity.IntegrityTokenRequest
import kotlinx.coroutines.suspendCancellableCoroutine
import java.security.SecureRandom
import java.util.Base64
import kotlin.coroutines.resume

data class IntegrityAttestation(
    val token: String?,
    val nonce: String?,
)

/**
 * Requests a Play Integrity token for enroll.
 * Returns null token when cloud project is unset (lab) or Play services fail — server then
 * accepts only if ELDERSHIELD_ENROLL_SKIP_INTEGRITY=1.
 */
object IntegrityTokenProvider {
    suspend fun request(context: Context): IntegrityAttestation {
        val projectNumber = BuildConfig.PLAY_CLOUD_PROJECT_NUMBER.trim()
        if (projectNumber.isEmpty() || projectNumber == "0") {
            return IntegrityAttestation(token = null, nonce = null)
        }
        val number =
            try {
                projectNumber.toLong()
            } catch (_: NumberFormatException) {
                return IntegrityAttestation(token = null, nonce = null)
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
                    if (cont.isActive) {
                        cont.resume(IntegrityAttestation(token = response.token(), nonce = nonce))
                    }
                }.addOnFailureListener {
                    if (cont.isActive) cont.resume(IntegrityAttestation(token = null, nonce = null))
                }
        }
    }

    private fun newNonce(): String {
        val bytes = ByteArray(24)
        SecureRandom().nextBytes(bytes)
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes)
    }
}
