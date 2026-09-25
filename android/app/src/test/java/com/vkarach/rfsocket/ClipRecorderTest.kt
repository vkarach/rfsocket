package com.vkarach.rfsocket

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

class ClipRecorderTest {

    private val fixtures = File("src/test/resources/clip_fixtures")

    private fun sampleFrames() = (0 until 3).map { i ->
        ByteArray(FRAME_SIZE) { b -> ((i * 37 + b) % 256).toByte() } to (100 + i * 50)
    }

    @Test
    fun idMatchesReferenceBuilder() {
        val recorder = ClipRecorder("sample clip.gif")
        sampleFrames().forEach { (frame, ms) -> recorder.add(frame, ms) }
        val built = recorder.finish()
        assertEquals(fixtures.resolve("sample_clip.id").readText().trim(), built.id)
    }

    @Test
    fun deviceCanDecompressTheStream() {
        val recorder = ClipRecorder("sample clip.gif")
        sampleFrames().forEach { (frame, ms) -> recorder.add(frame, ms) }
        val built = recorder.finish()
        val headerEnd = 4 + 1 + 4 + 1 + "sample clip.gif".length
        val compressed = built.data.copyOfRange(headerEnd, built.data.size)

        // Device inflate uses windowBits=10; must match or the device could never decode this.
        val inflater = com.jcraft.jzlib.Inflater(10)
        inflater.setInput(compressed)
        val out = ByteArray(3 * (2 + FRAME_SIZE))
        inflater.setOutput(out)
        while (inflater.totalOut < out.size && !inflater.finished()) {
            inflater.inflate(com.jcraft.jzlib.JZlib.Z_NO_FLUSH)
        }
        assertEquals(out.size.toLong(), inflater.totalOut)
    }
}
