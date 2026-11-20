package com.eldershield.ui

import android.Manifest
import android.app.role.RoleManager
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.eldershield.BuildConfig
import com.eldershield.R
import com.eldershield.data.IntegrityTokenProvider
import com.eldershield.data.ProvisionStore
import com.eldershield.service.CallScreeningRoleProbe
import kotlinx.coroutines.launch

/**
 * Debug: admin provision form. Release: silent Autoprovision + permissions only.
 * Long-press title on release → admin CallScreening controls.
 * SSOT §1.2.1: never auto-steal CallScreening from Bitdefender peers.
 */
class MainActivity : AppCompatActivity() {
    private lateinit var store: ProvisionStore

    private val roleLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) {
            refreshStatus()
        }

    private val permissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
            refreshStatus()
            maybeAutoRequestCallRole()
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        store = ProvisionStore(this)

        val baseUrl = findViewById<EditText>(R.id.baseUrl)
        val deviceKey = findViewById<EditText>(R.id.deviceKey)
        val save = findViewById<Button>(R.id.saveProvision)
        val labEnroll = findViewById<Button>(R.id.labEnroll)
        val requestRole = findViewById<Button>(R.id.requestCallRole)
        val title = findViewById<TextView>(R.id.title)

        if (BuildConfig.DEBUG) {
            title.text = "Admin provisioning (lab / debug)"
            baseUrl.setText(store.baseUrl().takeIf { it != "https://example.invalid" }.orEmpty())
            deviceKey.setText(store.deviceApiKey().orEmpty())
            save.setOnClickListener {
                val url = baseUrl.text?.toString()?.trim().orEmpty().trimEnd('/')
                val key = deviceKey.text?.toString()?.trim().orEmpty()
                if (url.isEmpty() || key.isEmpty()) {
                    findViewById<TextView>(R.id.status).text =
                        "Base URL and device API key are required."
                    return@setOnClickListener
                }
                store.saveManual(url, key)
                ensureScreeningPermissions()
                Autoprovision.enqueueWork(this)
                findViewById<TextView>(R.id.status).text =
                    "Saved. Sync + heartbeat enqueued.\n" + statusLine()
            }
            labEnroll.setOnClickListener {
                val url =
                    baseUrl.text?.toString()?.trim().orEmpty().trimEnd('/').ifBlank {
                        "http://127.0.0.1:8765"
                    }
                lifecycleScope.launch {
                    findViewById<TextView>(R.id.status).text = "Lab enroll…"
                    // Clear any prior key so Autoprovision takes the enroll path.
                    store.saveManual(url, "")
                    val outcome = Autoprovision.ensure(this@MainActivity, integrityToken = null)
                    findViewById<TextView>(R.id.status).text =
                        when (outcome) {
                            is Autoprovision.Outcome.AlreadyProvisioned ->
                                "Already provisioned.\n" + statusLine()
                            is Autoprovision.Outcome.Enrolled ->
                                "Lab enrolled.\n" + statusLine()
                            is Autoprovision.Outcome.Failed ->
                                "Lab enroll failed: ${outcome.reason}\n" + statusLine()
                        }
                }
            }
            requestRole.setOnClickListener {
                ensureScreeningPermissions()
                requestCallScreeningRole(explicitAdminTap = true)
            }
            refreshStatus()
            ensureScreeningPermissions()
        } else {
            title.text = "ElderShield"
            baseUrl.visibility = View.GONE
            deviceKey.visibility = View.GONE
            save.visibility = View.GONE
            labEnroll.visibility = View.GONE
            requestRole.visibility = View.GONE
            findViewById<TextView>(R.id.status).text = "Starting…"
            title.setOnLongClickListener {
                requestRole.visibility = View.VISIBLE
                refreshStatus()
                true
            }
            requestRole.setOnClickListener {
                ensureScreeningPermissions()
                requestCallScreeningRole(explicitAdminTap = true)
            }
            ensureScreeningPermissions()
            lifecycleScope.launch {
                val attestation = IntegrityTokenProvider.request(this@MainActivity)
                val outcome =
                    Autoprovision.ensure(
                        this@MainActivity,
                        integrityToken = attestation.token,
                        integrityNonce = attestation.nonce,
                    )
                findViewById<TextView>(R.id.status).text =
                    when (outcome) {
                        is Autoprovision.Outcome.AlreadyProvisioned ->
                            "Ready.\n" + statusLine()
                        is Autoprovision.Outcome.Enrolled ->
                            "Enrolled.\n" + statusLine()
                        is Autoprovision.Outcome.Failed ->
                            "Setup pending (${outcome.reason}).\n" + statusLine()
                    }
                maybeAutoRequestCallRole()
            }
        }
    }

    private fun maybeAutoRequestCallRole() {
        if (BuildConfig.DEBUG) return
        requestCallScreeningRole(explicitAdminTap = false)
    }

    private fun refreshStatus() {
        findViewById<TextView>(R.id.status).text = statusLine()
    }

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
                statusLine() +
                    "\n(skipped auto role request — peer screener present; Bitdefender 병행)"
            return
        }
        val rm = getSystemService(RoleManager::class.java) ?: return
        if (rm.isRoleAvailable(RoleManager.ROLE_CALL_SCREENING)) {
            if (explicitAdminTap && screening.peers.isNotEmpty()) {
                findViewById<TextView>(R.id.status).text =
                    "System may offer switching away from: ${screening.peers.joinToString()}. " +
                        "Cancel to keep Bitdefender. SSOT §1.2.1\n" +
                        statusLine()
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

    private fun statusLine(): String {
        val url = store.baseUrl()
        val keySet = store.hasToken()
        val screening = CallScreeningRoleProbe.probe(this)
        return "url=${if (url.isBlank() || url == "https://example.invalid") "(missing)" else url}\n" +
            "deviceKey=${if (keySet) "set" else "missing"}\n" +
            "callScreeningRole=${screening.heldByUs} heldBy=${screening.heldBy ?: "(none)"}\n" +
            "peers=${if (screening.peers.isEmpty()) "(none)" else screening.peers.joinToString()}\n" +
            "coexistence=${if (!screening.heldByUs && screening.peers.isNotEmpty()) "leave_peer" else "ok"}\n" +
            "readContacts=${hasPermission(Manifest.permission.READ_CONTACTS)}\n" +
            "readCallLog=${hasPermission(Manifest.permission.READ_CALL_LOG)}"
    }

    companion object {
        private val SCREENING_PERMISSIONS =
            arrayOf(
                Manifest.permission.READ_CONTACTS,
                Manifest.permission.READ_CALL_LOG,
                Manifest.permission.READ_PHONE_STATE,
            )
    }
}
