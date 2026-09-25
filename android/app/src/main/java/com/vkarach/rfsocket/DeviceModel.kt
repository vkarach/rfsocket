package com.vkarach.rfsocket

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import java.io.IOException
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

const val POLL_MS = 2000L
private const val BRIGHTNESS_DEBOUNCE_MS = 80L

interface DeviceApi {
    suspend fun states(): Map<String, Boolean>
    suspend fun set(channel: String, on: Boolean): Boolean
    suspend fun screen(): ScreenMode
    suspend fun pinScreen(mode: ScreenMode)
    suspend fun brightness(): Int
    suspend fun setBrightness(value: Int)
    suspend fun clips(): List<Clip>
    suspend fun play(id: String, once: Boolean)
    suspend fun stop()
    suspend fun star(id: String, starred: Boolean)
    suspend fun delete(id: String)
}

/** Null fields are not known yet; `reachable` stays null until the first answer or failure. */
data class DeviceState(
    val reachable: Boolean? = null,
    val channels: Map<String, Boolean>? = null,
    val screen: ScreenMode? = null,
    val brightness: Int? = null,
    val clips: List<Clip>? = null,
)

class DeviceModel(private val api: DeviceApi, private val pollMs: Long = POLL_MS) : ViewModel() {

    private val _state = MutableStateFlow(DeviceState())
    val state: StateFlow<DeviceState> = _state

    private val _messages = MutableSharedFlow<String>(extraBufferCapacity = 4)
    val messages: SharedFlow<String> = _messages

    private val refreshLock = Mutex()
    private var polling: Job? = null

    fun startPolling() {
        if (polling?.isActive == true) return
        polling = viewModelScope.launch {
            while (true) {
                refresh()
                delay(pollMs)
            }
        }
    }

    fun stopPolling() {
        polling?.cancel()
        polling = null
    }

    fun setChannel(channel: String, on: Boolean): Job = act { api.set(channel, on) }

    fun pinScreen(mode: ScreenMode): Job = act { api.pinScreen(mode) }

    // Debounced and applied optimistically: a full refresh per drag step visibly flickers the device.
    private var brightnessJob: Job? = null

    fun setBrightness(value: Int) {
        _state.update { it.copy(brightness = value) }
        brightnessJob?.cancel()
        brightnessJob = viewModelScope.launch {
            delay(BRIGHTNESS_DEBOUNCE_MS)
            try {
                api.setBrightness(value)
            } catch (e: IOException) {
                _state.update { it.copy(reachable = false) }
            }
        }
    }

    fun play(id: String, once: Boolean): Job = act { api.play(id, once) }

    fun stop(): Job = act { api.stop() }

    fun star(id: String, starred: Boolean): Job = act { api.star(id, starred) }

    fun delete(id: String): Job = act { api.delete(id) }

    private suspend fun refresh() = refreshLock.withLock {
        try {
            val channels = api.states()
            val screen = api.screen()
            val brightness = api.brightness()
            val clips = api.clips()
            _state.value = DeviceState(
                reachable = true, channels = channels, screen = screen, brightness = brightness, clips = clips,
            )
        } catch (e: IOException) {
            _state.update { it.copy(reachable = false) }
        }
    }

    private fun act(action: suspend () -> Unit): Job = viewModelScope.launch {
        try {
            action()
        } catch (e: NotFoundException) {
            _messages.tryEmit("Clip not found")
        } catch (e: IOException) {
            _state.update { it.copy(reachable = false) }
            return@launch
        }
        refresh()
    }
}
