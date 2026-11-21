package com.eldershield.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "call_evidence")
data class CallEvidenceEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val atEpochMs: Long,
    val countryIso: String?,
    val decision: String,
    val phoneHash: String,
    val last4: String?,
)
