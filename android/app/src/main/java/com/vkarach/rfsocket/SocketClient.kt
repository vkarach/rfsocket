package com.vkarach.rfsocket

import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class SocketClient(private val baseUrl: String) {

    suspend fun toggle(channel: String): Boolean = request("/$channel/toggle") == "on"

    suspend fun state(channel: String): Boolean {
        val entry = request("/state").split(" ").firstOrNull { it.startsWith("$channel:") }
            ?: throw IOException("channel $channel not reported")
        return entry.substringAfter(":") == "on"
    }

    private suspend fun request(path: String): String = withContext(Dispatchers.IO) {
        val connection = URL(baseUrl + path).openConnection() as HttpURLConnection
        connection.connectTimeout = 3000
        connection.readTimeout = 5000
        try {
            if (connection.responseCode != HttpURLConnection.HTTP_OK) {
                throw IOException("HTTP ${connection.responseCode}")
            }
            connection.inputStream.bufferedReader().use { it.readText().trim() }
        } finally {
            connection.disconnect()
        }
    }
}
