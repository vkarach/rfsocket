package com.vkarach.rfsocket

import java.io.IOException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test

private class FakeApi : DeviceApi {
    var reachable = true
    var channels = mapOf("a" to false)
    var screen = ScreenMode.Auto
    var clips = listOf(Clip("0123456789ab", "cat.gif", 10, 3, starred = false, playing = false))
    var polls = 0

    private fun check() {
        if (!reachable) throw IOException("down")
    }

    override suspend fun states(): Map<String, Boolean> {
        polls++
        check()
        return channels
    }

    override suspend fun set(channel: String, on: Boolean): Boolean {
        check()
        channels = channels + (channel to on)
        return on
    }

    override suspend fun screen(): ScreenMode {
        check()
        return screen
    }

    override suspend fun pinScreen(mode: ScreenMode) {
        check()
        screen = mode
    }

    override suspend fun clips(): List<Clip> {
        check()
        return clips
    }

    override suspend fun play(id: String, once: Boolean) {
        check()
        if (clips.none { it.id == id }) throw NotFoundException()
        clips = clips.map { it.copy(playing = it.id == id) }
    }

    override suspend fun stop() {
        check()
        clips = clips.map { it.copy(playing = false) }
    }

    override suspend fun star(id: String, starred: Boolean) {
        check()
        clips = clips.map { if (it.id == id) it.copy(starred = starred) else it }
    }

    override suspend fun delete(id: String) {
        check()
        clips = clips.filter { it.id != id }
    }
}

@OptIn(ExperimentalCoroutinesApi::class)
class DeviceModelTest {

    private val dispatcher = StandardTestDispatcher()
    private val api = FakeApi()

    @Before
    fun setUp() {
        Dispatchers.setMain(dispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    private fun model(): DeviceModel = DeviceModel(api, pollMs = 2000)

    @Test
    fun unknownUntilFirstPoll() = runTest(dispatcher) {
        val state = model().state.value
        assertNull(state.reachable)
        assertNull(state.channels)
    }

    @Test
    fun pollingFillsStateAndRepeats() = runTest(dispatcher) {
        val model = model()
        model.startPolling()
        runCurrent()

        val state = model.state.value
        assertEquals(true, state.reachable)
        assertEquals(mapOf("a" to false), state.channels)
        assertEquals(ScreenMode.Auto, state.screen)
        assertEquals(api.clips, state.clips)

        advanceTimeBy(4001)
        assertEquals(3, api.polls)
        model.stopPolling()
    }

    @Test
    fun stopPollingStopsRequests() = runTest(dispatcher) {
        val model = model()
        model.startPolling()
        runCurrent()
        model.stopPolling()

        advanceTimeBy(10_000)
        assertEquals(1, api.polls)
    }

    @Test
    fun reachabilityRecoversWithoutUserAction() = runTest(dispatcher) {
        val model = model()
        api.reachable = false
        model.startPolling()
        runCurrent()
        assertEquals(false, model.state.value.reachable)

        api.reachable = true
        advanceTimeBy(2001)
        assertEquals(true, model.state.value.reachable)
        model.stopPolling()
    }

    @Test
    fun actionRefreshesImmediately() = runTest(dispatcher) {
        val model = model()
        model.play("0123456789ab", once = false)
        advanceUntilIdle()

        assertEquals(true, model.state.value.clips!!.single().playing)
    }

    @Test
    fun channelAndScreenActionsRefresh() = runTest(dispatcher) {
        val model = model()
        model.setChannel("a", on = true)
        model.pinScreen(ScreenMode.Clock)
        advanceUntilIdle()

        assertEquals(mapOf("a" to true), model.state.value.channels)
        assertEquals(ScreenMode.Clock, model.state.value.screen)
    }

    @Test
    fun missingClipReportsMessage() = runTest(dispatcher) {
        val model = model()
        val message = async { model.messages.first() }
        runCurrent()
        model.play("ffffffffffff", once = true)
        advanceUntilIdle()

        assertEquals("Clip not found", message.await())
    }

    @Test
    fun failedActionMarksUnreachable() = runTest(dispatcher) {
        val model = model()
        api.reachable = false
        model.stop()
        advanceUntilIdle()

        assertEquals(false, model.state.value.reachable)
    }
}
