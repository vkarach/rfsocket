package com.vkarach.rfsocket

import com.jcraft.jzlib.Deflater
import com.jcraft.jzlib.JZlib
import java.security.MessageDigest

private const val NAME_MAX = 32
private const val ID_LENGTH = 12
private const val ZLIB_WBITS = 10
private const val DURATION_MAX_MS = 0xFFFF

data class RecordedClip(val id: String, val name: String, val frames: Int, val data: ByteArray)

private fun sanitizeName(name: String): String {
    val base = name.substringAfterLast('/').substringAfterLast('\\')
    return base.map { if (it in ' '..'~') it else '_' }.joinToString("").take(NAME_MAX)
}

/** Mirrors host/clip.py's ClipBuilder: header + zlib(records), record = u16 ms + 1024-byte frame. */
class ClipRecorder(name: String) {
    val name: String = sanitizeName(name)
    var frames: Int = 0
        private set
    var size: Int = 0
        private set

    private val digest = MessageDigest.getInstance("SHA-1")
    private val deflater = Deflater(JZlib.Z_BEST_COMPRESSION, ZLIB_WBITS)
    private val chunks = mutableListOf<ByteArray>()

    fun add(frame: ByteArray, durationMs: Int) {
        require(frame.size == FRAME_SIZE) { "frame must be $FRAME_SIZE bytes" }
        val ms = durationMs.coerceIn(1, DURATION_MAX_MS)
        val record = ByteArray(2 + FRAME_SIZE)
        record[0] = (ms shr 8).toByte()
        record[1] = ms.toByte()
        frame.copyInto(record, 2)
        digest.update(record)
        chunks += deflateChunk(record, JZlib.Z_NO_FLUSH)
        frames++
    }

    fun finish(): RecordedClip {
        chunks += deflateChunk(ByteArray(0), JZlib.Z_FINISH)
        val nameBytes = name.toByteArray(Charsets.US_ASCII)
        val header = byteArrayOf('R'.code.toByte(), 'F'.code.toByte(), 'C'.code.toByte(), 'L'.code.toByte(), 1) +
            intBytes(frames) + byteArrayOf(nameBytes.size.toByte()) + nameBytes
        val data = header + chunks.reduce { a, b -> a + b }
        val hash = digest.digest().joinToString("") { "%02x".format(it) }
        return RecordedClip(hash.take(ID_LENGTH), name, frames, data)
    }

    private fun deflateChunk(input: ByteArray, flush: Int): ByteArray {
        deflater.setInput(input)
        val buffer = ByteArray(maxOf(64, input.size + 64))
        val chunks = mutableListOf<ByteArray>()
        do {
            deflater.setOutput(buffer)
            val before = deflater.totalOut
            deflater.deflate(flush)
            val produced = (deflater.totalOut - before).toInt()
            if (produced > 0) chunks += buffer.copyOf(produced)
        } while (deflater.avail_in > 0 || (flush == JZlib.Z_FINISH && !deflater.finished()))
        size += chunks.sumOf { it.size }
        return if (chunks.isEmpty()) ByteArray(0) else chunks.reduce { a, b -> a + b }
    }

    private fun intBytes(value: Int) = byteArrayOf(
        (value ushr 24).toByte(), (value ushr 16).toByte(), (value ushr 8).toByte(), value.toByte(),
    )
}
