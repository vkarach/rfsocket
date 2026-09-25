package com.vkarach.rfsocket

import java.net.ServerSocket
import java.net.Socket
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class FrameTimerTest {

    @Test
    fun sendsFramesOnTimeAndDropsWhenBehind() {
        var now = 0L
        val timer = FrameTimer { now }
        val sent = mutableListOf<Int>()

        assertTrue(timer.next(100) { sent += 0 })   // first frame always sent
        now = 250                                    // 150ms late for a 100ms-duration frame
        assertFalse(timer.next(100) { sent += 1 })    // dropped: falling behind
        now = 260
        assertTrue(timer.next(100) { sent += 2 })     // caught up enough to send

        assertEquals(listOf(0, 2), sent)
    }
}

class StoreProtocolTest {

    @Test
    fun uploadSendsHeaderPayloadAndReadsFinalStatus() {
        val server = ServerSocket(0)
        val clip = ClipRecorder("t.gif").apply {
            add(ByteArray(FRAME_SIZE), 100)
        }.finish()

        val serverThread = Thread {
            server.accept().use { conn ->
                val input = conn.getInputStream()
                val fixed = ByteArray(14)
                input.read(fixed)
                val nameLen = fixed[13].toInt() and 0xFF
                input.readNBytes(nameLen)
                input.readNBytes(8)
                conn.getOutputStream().write(byteArrayOf(0)) // ACCEPT
                var remaining = clip.data.size
                val buf = ByteArray(4096)
                while (remaining > 0) {
                    val n = input.read(buf, 0, minOf(buf.size, remaining))
                    if (n <= 0) break
                    remaining -= n
                }
                conn.getOutputStream().write(byteArrayOf(4)) // DONE
            }
        }
        serverThread.start()

        val socket = Socket("127.0.0.1", server.localPort)
        val status = StoreProtocol.upload(socket, clip, keep = false)
        serverThread.join(2000)
        server.close()

        assertEquals(4, status)
    }
}
