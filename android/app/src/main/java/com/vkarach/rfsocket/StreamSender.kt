package com.vkarach.rfsocket

import java.io.DataInputStream
import java.io.DataOutputStream
import java.net.Socket

const val STORE_ACCEPT = 0
const val STORE_EXISTS = 1
const val STORE_TOO_LARGE = 2
const val STORE_NO_SPACE = 3
const val STORE_DONE = 4
const val STORE_FAILED = 5

private const val MSG_FRAME = 0x01
private const val MSG_STORE = 0x02
private const val UPLOAD_CHUNK = 4096

fun frameMessage(frame: ByteArray): ByteArray {
    require(frame.size == FRAME_SIZE) { "frame must be $FRAME_SIZE bytes" }
    return byteArrayOf(MSG_FRAME.toByte()) + frame
}

/** Sleeps until a frame's due time, never drops - backpressure against a slow device is the caller's job. */
class FrameTimer(private val clock: () -> Long = System::currentTimeMillis) {
    private var due: Long? = null

    fun next(durationMs: Int, send: () -> Unit) {
        val now = clock()
        val target = due ?: now
        val wait = target - now
        if (wait > 0) Thread.sleep(wait)
        send()
        due = target + durationMs
    }
}

object StoreProtocol {
    /** Mirrors host/sender.py's store(): header, wait ACCEPT, stream payload, read final status. */
    fun upload(socket: Socket, clip: RecordedClip, keep: Boolean): Int {
        val out = DataOutputStream(socket.getOutputStream())
        val input = DataInputStream(socket.getInputStream())
        val nameBytes = clip.name.toByteArray(Charsets.US_ASCII)

        out.writeByte(MSG_STORE)
        out.writeBytes(clip.id.padEnd(12, ' ').take(12))
        out.writeByte(if (keep) 1 else 0)
        out.writeByte(nameBytes.size)
        out.write(nameBytes)
        out.writeInt(clip.frames)
        out.writeInt(clip.data.size)
        out.flush()

        val accept = input.readUnsignedByte()
        if (accept != STORE_ACCEPT) return accept

        var offset = 0
        while (offset < clip.data.size) {
            val chunk = minOf(UPLOAD_CHUNK, clip.data.size - offset)
            out.write(clip.data, offset, chunk)
            offset += chunk
        }
        out.flush()
        return input.readUnsignedByte()
    }
}
