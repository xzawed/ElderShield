package com.eldershield.domain.sync

/**
 * Short codes stored on the device and reported as lastSyncErrorCode.
 * Never includes response bodies or hostnames.
 */
object SyncErrorCodes {
    fun fromThrowable(error: Throwable?): String {
        if (error == null) return "network"
        val msg = buildString {
            var current: Throwable? = error
            var guard = 0
            while (current != null && guard < 8) {
                current.message?.let { part ->
                    if (isNotEmpty()) append(' ')
                    append(part)
                }
                current = current.cause
                guard++
            }
        }
        val http = Regex("""HTTP\s+(\d{3})""").find(msg)?.groupValues?.getOrNull(1)?.toIntOrNull()
        if (http != null) {
            return when (http) {
                in 400..499 -> "http_4xx"
                in 500..599 -> "http_5xx"
                else -> "network"
            }
        }
        val blob = "${error::class.simpleName.orEmpty()} $msg"
        if (blob.contains("JSON", ignoreCase = true) || blob.contains("parse", ignoreCase = true)) {
            return "parse"
        }
        return "network"
    }
}
