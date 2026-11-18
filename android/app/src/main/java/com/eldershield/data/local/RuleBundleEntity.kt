package com.eldershield.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "rule_bundle_cache")
data class RuleBundleEntity(
    @PrimaryKey val id: Int = 1,
    val version: Int,
    val payloadJson: String,
    val updatedAt: String?,
)
