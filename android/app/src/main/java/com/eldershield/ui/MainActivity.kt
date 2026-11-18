package com.eldershield.ui

import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.eldershield.R

/** Minimal settings/status surface for admin testing — no parent-facing alerts. */
class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        findViewById<TextView>(R.id.status).text = "ElderShield installed. Rules sync in background."
    }
}
