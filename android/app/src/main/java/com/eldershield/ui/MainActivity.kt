package com.eldershield.ui

import android.app.role.RoleManager
import android.content.Context
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import com.eldershield.R
import com.eldershield.service.DeviceReportWorker
import com.eldershield.service.RuleSyncWorker

/**
 * Admin/installer provisioning only — not a parent-facing control surface.
 * Saves base_url + device_api_key, enqueues immediate sync, requests call-screening role.
 */
class MainActivity : AppCompatActivity() {
    private val roleLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) {
            refreshStatus()
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val prefs = getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val baseUrl = findViewById<EditText>(R.id.baseUrl)
        val deviceKey = findViewById<EditText>(R.id.deviceKey)

        baseUrl.setText(prefs.getString(KEY_BASE_URL, "") ?: "")
        deviceKey.setText(prefs.getString(KEY_DEVICE_API_KEY, "") ?: "")
        refreshStatus()

        findViewById<Button>(R.id.saveProvision).setOnClickListener {
            val url = baseUrl.text?.toString()?.trim().orEmpty().trimEnd('/')
            val key = deviceKey.text?.toString()?.trim().orEmpty()
            if (url.isEmpty() || key.isEmpty()) {
                findViewById<TextView>(R.id.status).text = "Base URL and device API key are required."
                return@setOnClickListener
            }
            prefs.edit()
                .putString(KEY_BASE_URL, url)
                .putString(KEY_DEVICE_API_KEY, key)
                .apply()
            enqueueImmediateWork()
            findViewById<TextView>(R.id.status).text =
                "Saved. Sync + heartbeat enqueued.\n" + statusLine(prefs)
        }

        findViewById<Button>(R.id.requestCallRole).setOnClickListener {
            requestCallScreeningRole()
        }
    }

    private fun refreshStatus() {
        val prefs = getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        findViewById<TextView>(R.id.status).text = statusLine(prefs)
    }

    private fun enqueueImmediateWork() {
        val wm = WorkManager.getInstance(this)
        wm.enqueue(OneTimeWorkRequestBuilder<RuleSyncWorker>().build())
        wm.enqueue(OneTimeWorkRequestBuilder<DeviceReportWorker>().build())
    }

    private fun requestCallScreeningRole() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            refreshStatus()
            return
        }
        val rm = getSystemService(RoleManager::class.java) ?: return
        if (rm.isRoleHeld(RoleManager.ROLE_CALL_SCREENING)) {
            refreshStatus()
            return
        }
        if (rm.isRoleAvailable(RoleManager.ROLE_CALL_SCREENING)) {
            roleLauncher.launch(rm.createRequestRoleIntent(RoleManager.ROLE_CALL_SCREENING))
        } else {
            refreshStatus()
        }
    }

    private fun statusLine(prefs: android.content.SharedPreferences): String {
        val url = prefs.getString(KEY_BASE_URL, null).orEmpty()
        val keySet = !prefs.getString(KEY_DEVICE_API_KEY, null).isNullOrBlank()
        val role =
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val rm = getSystemService(RoleManager::class.java)
                rm?.isRoleHeld(RoleManager.ROLE_CALL_SCREENING) == true
            } else {
                false
            }
        return "url=${if (url.isBlank()) "(missing)" else url}\n" +
            "deviceKey=${if (keySet) "set" else "missing"}\n" +
            "callScreeningRole=$role"
    }

    companion object {
        const val PREFS = "eldershield"
        const val KEY_BASE_URL = "base_url"
        const val KEY_DEVICE_API_KEY = "device_api_key"
    }
}
