package com.vkarach.rfsocket

import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class NotFoundException : IOException("not found")

class SocketClient(private val baseUrl: String) : DeviceApi {

    override suspend fun states(): Map<String, Boolean> = parseStates(request("/state"))

    override suspend fun set(channel: String, on: Boolean): Boolean =
        request("/$channel/" + if (on) "on" else "off") == "on"

    override suspend fun screen(): ScreenMode = parseScreenMode(request("/screen"))

    override suspend fun pinScreen(mode: ScreenMode) {
        request("/screen/${mode.path}")
    }

    override suspend fun clips(): List<Clip> = parseClips(request("/clips"))

    override suspend fun play(id: String, once: Boolean) {
        request("/clips/$id/play" + if (once) "?once" else "")
    }

    override suspend fun stop() {
        request("/clips/stop")
    }

    override suspend fun star(id: String, starred: Boolean) {
        request("/clips/$id/" + if (starred) "star" else "unstar")
    }

    override suspend fun delete(id: String) {
        request("/clips/$id/delete")
    }

    private suspend fun request(path: String): String = withContext(Dispatchers.IO) {
        val connection = URL(baseUrl + path).openConnection() as HttpURLConnection
        connection.connectTimeout = 3000
        connection.readTimeout = 5000
        try {
            when (connection.responseCode) {
                HttpURLConnection.HTTP_OK -> connection.inputStream.bufferedReader().use { it.readText().trim() }
                HttpURLConnection.HTTP_NOT_FOUND -> throw NotFoundException()
                else -> throw IOException("HTTP ${connection.responseCode}")
            }
        } finally {
            connection.disconnect()
        }
    }
}
