package com.vkarach.rfsocket

import java.io.File
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertTrue
import org.junit.Test

private val FIXTURES = File("src/test/resources/convert_fixtures")

private fun fixture(name: String) = FIXTURES.resolve(name).readBytes()

class ConvertTest {

    @Test
    fun packVlsbMatchesReference() {
        val bits = BooleanArray(FRAME_WIDTH * FRAME_HEIGHT) { i ->
            val x = i % FRAME_WIDTH
            val y = i / FRAME_WIDTH
            (x % 2 == 0) == (y % 2 == 0)
        }
        assertArrayEquals(fixture("checkerboard_packed.bin"), packVlsb(bits))
    }

    @Test
    fun bayerDitherMatchesReference() {
        val gray = fixture("gradient_input.bin").map { it.toInt() and 0xFF }.toIntArray()
        assertArrayEquals(fixture("dither_bayer.bin"), packVlsb(ditherBayer(gray)))
        assertArrayEquals(
            fixture("dither_bayer_inverted.bin"),
            packVlsb(BooleanArray(gray.size) { !ditherBayer(gray)[it] }),
        )
    }

    @Test
    fun noneDitherMatchesReference() {
        val gray = fixture("gradient_input.bin").map { it.toInt() and 0xFF }.toIntArray()
        assertArrayEquals(fixture("dither_none.bin"), packVlsb(ditherNone(gray)))
    }

    @Test
    fun fsDitherIsDeterministicAndHandlesExtremes() {
        val black = IntArray(FRAME_WIDTH * FRAME_HEIGHT) { 0 }
        val white = IntArray(FRAME_WIDTH * FRAME_HEIGHT) { 255 }
        assertTrue(ditherFs(black).none { it })
        assertTrue(ditherFs(white).all { it })

        val gray = fixture("gradient_input.bin").map { it.toInt() and 0xFF }.toIntArray()
        assertArrayEquals(ditherFs(gray), ditherFs(gray))
    }
}
