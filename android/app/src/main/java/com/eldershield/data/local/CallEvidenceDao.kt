package com.eldershield.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query

@Dao
interface CallEvidenceDao {
    @Insert
    suspend fun insert(entity: CallEvidenceEntity): Long

    @Query(
        "SELECT * FROM call_evidence WHERE atEpochMs BETWEEN :fromMs AND :toMs ORDER BY atEpochMs ASC",
    )
    suspend fun listBetween(fromMs: Long, toMs: Long): List<CallEvidenceEntity>

    @Query("SELECT COUNT(*) FROM call_evidence")
    suspend fun count(): Int

    @Query(
        "DELETE FROM call_evidence WHERE id NOT IN (SELECT id FROM call_evidence ORDER BY atEpochMs DESC LIMIT :keep)",
    )
    suspend fun trimToMax(keep: Int = 200)
}
