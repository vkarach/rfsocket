package com.vkarach.rfsocket

import java.io.IOException
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class ClipsTest {

    @Test
    fun parsesFieldsAndKeepsSpacesInName() {
        val clips = parseClips("0123456789ab 120 34 * > my cat.gif\nba9876543210 5 2 - - dog.png")
        assertEquals(
            listOf(
                Clip("0123456789ab", "my cat.gif", 120, 34, starred = true, playing = true),
                Clip("ba9876543210", "dog.png", 5, 2, starred = false, playing = false),
            ),
            clips,
        )
    }

    @Test
    fun emptyBodyIsEmptyList() {
        assertEquals(emptyList<Clip>(), parseClips(""))
    }

    @Test
    fun missingNameAfterTrimIsEmpty() {
        assertEquals("", parseClips("0123456789ab 1 1 - -").single().name)
    }

    @Test
    fun malformedLineThrows() {
        assertThrows(IOException::class.java) { parseClips("0123456789ab x 1 - - a") }
        assertThrows(IOException::class.java) { parseClips("0123456789ab 1 1") }
    }
}
