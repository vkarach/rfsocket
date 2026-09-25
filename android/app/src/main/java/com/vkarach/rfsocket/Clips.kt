package com.vkarach.rfsocket

import java.io.IOException

data class Clip(
    val id: String,
    val name: String,
    val frames: Int,
    val sizeKb: Int,
    val starred: Boolean,
    val playing: Boolean,
)

/** Parses the `/clips` body: one `id frames KB star playing name` line per clip, newest first. */
fun parseClips(body: String): List<Clip> = body.lines().filter { it.isNotBlank() }.map { line ->
    val fields = line.trim().split(" ", limit = 6)
    val frames = fields.getOrNull(1)?.toIntOrNull()
    val sizeKb = fields.getOrNull(2)?.toIntOrNull()
    if (fields.size < 5 || frames == null || sizeKb == null) {
        throw IOException("malformed clip line: $line")
    }
    Clip(fields[0], fields.getOrElse(5) { "" }, frames, sizeKb, fields[3] == "*", fields[4] == ">")
}
