package com.vkarach.rfsocket

import java.io.IOException
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class ChannelsTest {

    @Test
    fun parsesStatesInOrder() {
        assertEquals(
            listOf("a" to true, "b" to false),
            parseStates("a:on b:off").toList(),
        )
    }

    @Test
    fun emptyBodyIsNoChannels() {
        assertEquals(emptyMap<String, Boolean>(), parseStates(""))
    }

    @Test
    fun malformedStateThrows() {
        assertThrows(IOException::class.java) { parseStates("a:maybe") }
        assertThrows(IOException::class.java) { parseStates("a") }
    }

    @Test
    fun parsesScreenModes() {
        assertEquals(ScreenMode.Auto, parseScreenMode("auto"))
        assertEquals(ScreenMode.Clock, parseScreenMode("clock"))
        assertThrows(IOException::class.java) { parseScreenMode("disco") }
    }
}
