package com.eldershield.ui

import android.Manifest
import android.app.role.RoleManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import com.eldershield.R
import com.eldershield.service.CallScreeningRoleProbe
import com.eldershield.service.DeviceReportWorker
import com.eldershield.service.RuleSyncWorker

/**
 * Admin/installer provisioning only — not a parent-facing control surface.
 * SSOT §1.2.1: never auto-steal CallScreening from Bitdefender peers.
 */
class MainActivity : AppCompatActivity() {
    private val roleLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) {
            refreshStatus()
        }

    private val permissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
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
        ensureScreeningPermissions()

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
            ensureScreeningPermissions()
            enqueueImmediateWork()
            // §1.2.1: do not auto-request role when Bitdefender (or peer) is installed.
            findViewById<TextView>(R.id.status).text =
                "Saved. Sync + heartbeat enqueued.\n" + statusLine(prefs)
        }

        findViewById<Button>(R.id.requestCallRole).setOnClickListener {
            ensureScreeningPermissions()
            requestCallScreeningRole(explicitAdminTap = true)
        }
    }

    private fun refreshStatus() {
        val prefs = getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        findViewById<TextView>(R.id.status).text = statusLine(prefs)
    }

    private fun enqueueImmediateWork() {
        val wm = WorkManager.getInstance(this)
        // Unique names — avoid parallel sync racing ActiveRuleBundleCache / Room.
        wm.enqueueUniqueWork(
            "${RuleSyncWorker.UNIQUE_NAME}-now",
            ExistingWorkPolicy.REPLACE,
            OneTimeWorkRequestBuilder<RuleSyncWorker>().build(),
        )
        wm.enqueueUniqueWork(
            "${DeviceReportWorker.UNIQUE_NAME}-now",
            ExistingWorkPolicy.REPLACE,
            OneTimeWorkRequestBuilder<DeviceReportWorker>().build(),
        )
    }

    /**
     * @param explicitAdminTap when false, skip if peers installed (coexistence).
     * When true, may show system switch UI — admin can cancel; never force via adb.
     */
    private fun requestCallScreeningRole(explicitAdminTap: Boolean) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            refreshStatus()
            return
        }
        val screening = CallScreeningRoleProbe.probe(this)
        if (screening.heldByUs) {
            refreshStatus()
            return
        }
        if (!explicitAdminTap && CallScreeningRoleProbe.shouldAvoidAutoRoleRequest(this)) {
            findViewById<TextView>(R.id.status).text =
                statusLine(getSharedPreferences(PREFS, Context.MODE_PRIVATE)) +
                    "\n(skipped auto role request — peer screener present; Bitdefender 병행)"
            return
        }
        val rm = getSystemService(RoleManager::class.java) ?: return
        if (rm.isRoleAvailable(RoleManager.ROLE_CALL_SCREENING)) {
            if (explicitAdminTap && screening.peers.isNotEmpty()) {
                findViewById<TextView>(R.id.status).text =
                    "System may offer switching away from: ${screening.peers.joinToString()}. " +
                        "Cancel to keep Bitdefender. SSOT §1.2.1\n" +
                        statusLine(getSharedPreferences(PREFS, Context.MODE_PRIVATE))
            }
            roleLauncher.launch(rm.createRequestRoleIntent(RoleManager.ROLE_CALL_SCREENING))
        } else {
            refreshStatus()
        }
    }

    private fun ensureScreeningPermissions() {
        val needed =
            SCREENING_PERMISSIONS.filter {
                ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
            }
        if (needed.isNotEmpty()) {
            permissionLauncher.launch(needed.toTypedArray())
        }
    }

    private fun hasPermission(name: String): Boolean =
        ContextCompat.checkSelfPermission(this, name) == PackageManager.PERMISSION_GRANTED

    private fun statusLine(prefs: android.content.SharedPreferences): String {
        val url = prefs.getString(KEY_BASE_URL, null).orEmpty()
        val keySet = !prefs.getString(KEY_DEVICE_API_KEY, null).isNullOrBlank()
        val screening = CallScreeningRoleProbe.probe(this)
        return "url=${if (url.isBlank()) "(missing)" else url}\n" +
            "deviceKey=${if (keySet) "set" else "missing"}\n" +
            "callScreeningRole=${screening.heldByUs} heldBy=${screening.heldBy ?: "(none)"}\n" +
            "peers=${if (screening.peers.isEmpty()) "(none)" else screening.peers.joinToString()}\n" +
            "coexistence=${if (!screening.heldByUs && screening.peers.isNotEmpty()) "leave_peer" else "ok"}\n" +
            "readContacts=${hasPermission(Manifest.permission.READ_CONTACTS)}\n" +
            "readCallLog=${hasPermission(Manifest.permission.READ_CALL_LOG)}"
    }

    companion object {
        const val PREFS = "eldershield"
        const val KEY_BASE_URL = "base_url"
        const val KEY_DEVICE_API_KEY = "device_api_key"

        private val SCREENING_PERMISSIONS =
            arrayOf(
                Manifest.permission.READ_CONTACTS,
                Manifest.permission.READ_CALL_LOG,
                Manifest.permission.READ_PHONE_STATE,
            )
    }
}
