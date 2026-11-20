package com.eldershield.data

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.eldershield.service.RuleSyncWorker

/**
 * Stores base URL + per-device API token. Prefer EncryptedSharedPreferences;
 * mirrors keys into the plain prefs file workers historically read.
 */
class ProvisionStore(context: Context) {
    private val app = context.applicationContext
    private val secure: SharedPreferences = createSecurePrefs(app)
    private val legacy: SharedPreferences =
        app.getSharedPreferences(RuleSyncWorker.PREFS, Context.MODE_PRIVATE)

    fun hasToken(): Boolean = !deviceApiKey().isNullOrBlank()

    fun baseUrl(): String {
        val fromSecure = secure.getString(KEY_BASE_URL, null)
        if (!fromSecure.isNullOrBlank()) return fromSecure.trimEnd('/')
        return legacy.getString(KEY_BASE_URL, RuleSyncWorker.DEFAULT_BASE_URL)
            ?.trimEnd('/')
            ?: RuleSyncWorker.DEFAULT_BASE_URL
    }

    fun deviceApiKey(): String? {
        val t = secure.getString(KEY_DEVICE_API_KEY, null)
        if (!t.isNullOrBlank()) return t
        return legacy.getString(KEY_DEVICE_API_KEY, null)
    }

    fun deviceUuid(): String? =
        secure.getString(KEY_DEVICE_UUID, null) ?: legacy.getString(KEY_DEVICE_UUID, null)

    fun saveEnrollment(baseUrl: String, deviceUuid: String, deviceToken: String) {
        val url = baseUrl.trim().trimEnd('/')
        secure.edit()
            .putString(KEY_BASE_URL, url)
            .putString(KEY_DEVICE_UUID, deviceUuid)
            .putString(KEY_DEVICE_API_KEY, deviceToken)
            .apply()
        legacy.edit()
            .putString(KEY_BASE_URL, url)
            .putString(KEY_DEVICE_UUID, deviceUuid)
            .putString(KEY_DEVICE_API_KEY, deviceToken)
            .apply()
    }

    fun saveManual(baseUrl: String, deviceApiKey: String) {
        val url = baseUrl.trim().trimEnd('/')
        secure.edit()
            .putString(KEY_BASE_URL, url)
            .putString(KEY_DEVICE_API_KEY, deviceApiKey)
            .apply()
        legacy.edit()
            .putString(KEY_BASE_URL, url)
            .putString(KEY_DEVICE_API_KEY, deviceApiKey)
            .apply()
    }

    companion object {
        const val KEY_BASE_URL = "base_url"
        const val KEY_DEVICE_API_KEY = "device_api_key"
        const val KEY_DEVICE_UUID = "device_uuid"

        private fun createSecurePrefs(context: Context): SharedPreferences {
            return try {
                val masterKey =
                    MasterKey.Builder(context)
                        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                        .build()
                EncryptedSharedPreferences.create(
                    context,
                    "eldershield_secure",
                    masterKey,
                    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
                )
            } catch (_: Exception) {
                context.getSharedPreferences("eldershield_secure_fallback", Context.MODE_PRIVATE)
            }
        }
    }
}
