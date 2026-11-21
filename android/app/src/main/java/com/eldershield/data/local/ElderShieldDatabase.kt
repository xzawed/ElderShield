package com.eldershield.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [RuleBundleEntity::class, CallEvidenceEntity::class],
    version = 2,
    exportSchema = false,
)
abstract class ElderShieldDatabase : RoomDatabase() {
    abstract fun ruleBundleDao(): RuleBundleDao
    abstract fun callEvidenceDao(): CallEvidenceDao

    companion object {
        @Volatile private var instance: ElderShieldDatabase? = null

        fun get(context: Context): ElderShieldDatabase =
            instance ?: synchronized(this) {
                instance
                    ?: Room.databaseBuilder(
                        context.applicationContext,
                        ElderShieldDatabase::class.java,
                        "eldershield.db",
                    )
                        .fallbackToDestructiveMigration()
                        .build()
                        .also { instance = it }
            }
    }
}
