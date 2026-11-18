package com.eldershield.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(entities = [RuleBundleEntity::class], version = 1, exportSchema = false)
abstract class ElderShieldDatabase : RoomDatabase() {
    abstract fun ruleBundleDao(): RuleBundleDao

    companion object {
        @Volatile private var instance: ElderShieldDatabase? = null

        fun get(context: Context): ElderShieldDatabase =
            instance ?: synchronized(this) {
                instance
                    ?: Room.databaseBuilder(
                        context.applicationContext,
                        ElderShieldDatabase::class.java,
                        "eldershield.db",
                    ).build().also { instance = it }
            }
    }
}
