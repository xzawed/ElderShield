package com.eldershield.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface RuleBundleDao {
    @Query("SELECT * FROM rule_bundle_cache WHERE id = 1 LIMIT 1")
    suspend fun get(): RuleBundleEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(entity: RuleBundleEntity)
}
