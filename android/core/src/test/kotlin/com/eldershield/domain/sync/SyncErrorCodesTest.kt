package com.eldershield.domain.sync

import org.json.JSONException
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

class SyncErrorCodesTest {
    @Test
    fun httpClassesAndParse() {
        assertEquals("http_4xx", SyncErrorCodes.fromThrowable(IllegalStateException("rules/latest HTTP 401")))
        assertEquals("http_5xx", SyncErrorCodes.fromThrowable(IllegalStateException("rules/latest HTTP 503")))
        assertEquals("parse", SyncErrorCodes.fromThrowable(JSONException("bad")))
        assertEquals("network", SyncErrorCodes.fromThrowable(java.io.IOException("timeout")))
        assertEquals("network", SyncErrorCodes.fromThrowable(null))
    }
}
