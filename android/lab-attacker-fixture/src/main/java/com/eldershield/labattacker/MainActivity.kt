package com.eldershield.labattacker

import android.app.Activity
import android.os.Bundle
import android.widget.TextView

/** Harmless placeholder UI — capabilities live only in the manifest for scanner scoring. */
class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val tv = TextView(this)
        tv.text = "ElderShield lab attacker fixture (inert)"
        setContentView(tv)
    }
}
