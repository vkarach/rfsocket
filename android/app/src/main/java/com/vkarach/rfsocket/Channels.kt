package com.vkarach.rfsocket

import java.io.IOException

enum class ScreenMode(val path: String, val label: String) {
    Auto("auto", "Auto"),
    Status("status", "Status"),
    Clock("clock", "Clock"),
    Off("off", "Off"),
}

/** Parses the `/state` body: space-separated `name:on|off` pairs, device order kept. */
fun parseStates(body: String): Map<String, Boolean> =
    body.split(" ").filter { it.isNotEmpty() }.associate { pair ->
        val fields = pair.split(":")
        val on = when (fields.getOrNull(1)) {
            "on" -> true
            "off" -> false
            else -> null
        }
        if (fields.size != 2 || fields[0].isEmpty() || on == null) {
            throw IOException("malformed state: $pair")
        }
        fields[0] to on
    }

fun parseScreenMode(body: String): ScreenMode =
    ScreenMode.entries.firstOrNull { it.path == body } ?: throw IOException("unknown screen: $body")
