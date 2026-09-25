package com.vkarach.rfsocket

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.net.Uri
import android.os.IBinder
import java.io.IOException
import java.net.Socket
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class StreamSettings(
    val scaleMode: ScaleMode = ScaleMode.Fit,
    val dither: DitherMethod = DitherMethod.Auto,
    val invert: Boolean = false,
    val loop: Boolean = true,
    val star: Boolean = false,
)

data class StreamState(val name: String, val settings: StreamSettings, val previewFrame: ByteArray)

private const val CHANNEL_ID = "streaming"
private const val NOTIFICATION_ID = 1
private const val ACTION_STOP = "com.vkarach.rfsocket.STOP_STREAM"
// Matches host/oled.py's Recorder cap: anything larger can never be stored.
private const val HISTORY_MAX_BYTES = 1024 * 1024

object StreamController {
    private val _outcome = MutableSharedFlow<String>(extraBufferCapacity = 4)
    val outcome: SharedFlow<String> = _outcome

    private val _active = MutableStateFlow<StreamState?>(null)
    val active: StateFlow<StreamState?> = _active

    @Volatile internal var settings = StreamSettings()
    @Volatile internal var settingsChanged = false
    @Volatile internal var stopRequested = false

    fun start(
        context: Context,
        uri: Uri,
        mimeType: String?,
        name: String,
        host: String,
        port: Int,
        settings: StreamSettings,
    ) {
        this.settings = settings
        val intent = Intent(context, StreamService::class.java).apply {
            putExtra("uri", uri)
            putExtra("mimeType", mimeType)
            putExtra("name", name)
            putExtra("host", host)
            putExtra("port", port)
        }
        context.startForegroundService(intent)
    }

    fun updateSettings(settings: StreamSettings) {
        this.settings = settings
        settingsChanged = true
        _active.value = _active.value?.copy(settings = settings)
    }

    fun stop() {
        stopRequested = true
    }

    internal fun setActive(state: StreamState?) {
        _active.value = state
    }

    internal fun reportOutcome(message: String) {
        _outcome.tryEmit(message)
    }
}

class StreamService : Service() {

    private val scope = CoroutineScope(Dispatchers.IO + Job())

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            StreamController.stop()
            return START_NOT_STICKY
        }
        val uri = intent?.getParcelableExtra<Uri>("uri") ?: return START_NOT_STICKY
        val mimeType = intent.getStringExtra("mimeType")
        val name = intent.getStringExtra("name") ?: "stream"
        val host = intent.getStringExtra("host")!!
        val port = intent.getIntExtra("port", 7000)

        ensureChannel()
        startForeground(NOTIFICATION_ID, buildNotification(name), ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        StreamController.stopRequested = false

        scope.launch {
            runStream(uri, mimeType, name, host, port)
            stopForeground(STOP_FOREGROUND_REMOVE)
            StreamController.setActive(null)
            stopSelf()
        }
        return START_NOT_STICKY
    }

    private fun runStream(uri: Uri, mimeType: String?, name: String, host: String, port: Int) {
        val source = try {
            openMediaSource(applicationContext, uri, mimeType)
        } catch (e: IllegalArgumentException) {
            StreamController.reportOutcome("error: ${e.message}")
            return
        }
        val autoDither = if (source is ImageSource) DitherMethod.Fs else DitherMethod.Bayer

        var recorder = ClipRecorder(name)
        var recordingComplete = false
        var recordingTooLarge = false
        val timer = FrameTimer()

        try {
            Socket(host, port).use { socket ->
                val out = socket.getOutputStream()
                var settingsAtPassStart = StreamController.settings
                var firstPassDone = false
                var looping = true

                while (looping && !StreamController.stopRequested) {
                    for ((bitmap, durationMs) in source.frames()) {
                        if (StreamController.stopRequested) break
                        if (StreamController.settingsChanged) {
                            StreamController.settingsChanged = false
                            settingsAtPassStart = StreamController.settings
                            recorder = ClipRecorder(name)
                            recordingComplete = false
                            recordingTooLarge = false
                        }
                        val effectiveDither = if (settingsAtPassStart.dither == DitherMethod.Auto) {
                            autoDither
                        } else {
                            settingsAtPassStart.dither
                        }
                        val frame = toFrame(bitmap, settingsAtPassStart.scaleMode, effectiveDither, settingsAtPassStart.invert)
                        bitmap.recycle()

                        timer.next(durationMs) { out.write(frameMessage(frame)) }
                        StreamController.setActive(StreamState(name, settingsAtPassStart, frame))

                        if (!firstPassDone && !recordingTooLarge) {
                            recorder.add(frame, durationMs.coerceAtLeast(1))
                            if (recorder.size > HISTORY_MAX_BYTES) recordingTooLarge = true
                        }
                    }
                    if (!firstPassDone) {
                        firstPassDone = true
                        recordingComplete = !recordingTooLarge
                    }
                    looping = settingsAtPassStart.loop && source !is ImageSource && !StreamController.stopRequested
                }
                if (source is ImageSource) {
                    while (!StreamController.stopRequested) Thread.sleep(200)
                }
            }
        } catch (e: IOException) {
            StreamController.reportOutcome("error: ${e.message}")
            return
        }

        if (!recordingComplete) {
            StreamController.reportOutcome("not saved: first pass incomplete")
            return
        }
        if (recordingTooLarge) {
            StreamController.reportOutcome("not saved: too large for history")
            return
        }
        uploadToHistory(recorder.finish(), host, port)
    }

    private fun uploadToHistory(clip: RecordedClip, host: String, port: Int) {
        try {
            Socket(host, port).use { socket ->
                when (StoreProtocol.upload(socket, clip, StreamController.settings.star)) {
                    STORE_DONE -> StreamController.reportOutcome("saved ${clip.id}")
                    STORE_EXISTS -> StreamController.reportOutcome("already saved ${clip.id}")
                    STORE_TOO_LARGE -> StreamController.reportOutcome("not saved: too large for history")
                    STORE_NO_SPACE -> StreamController.reportOutcome("not saved: no space (starred clips fill the budget)")
                    else -> StreamController.reportOutcome("error: device rejected the upload")
                }
            }
        } catch (e: IOException) {
            StreamController.reportOutcome("error: ${e.message}")
        }
    }

    private fun ensureChannel() {
        val manager = getSystemService(NotificationManager::class.java)
        if (manager.getNotificationChannel(CHANNEL_ID) == null) {
            manager.createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "Streaming", NotificationManager.IMPORTANCE_LOW),
            )
        }
    }

    private fun buildNotification(name: String): Notification {
        val stopIntent = PendingIntent.getService(
            this, 0,
            Intent(this, StreamService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_IMMUTABLE,
        )
        return Notification.Builder(this, CHANNEL_ID)
            .setContentTitle("Streaming $name")
            .setSmallIcon(R.drawable.ic_power)
            .addAction(Notification.Action.Builder(null, "Stop", stopIntent).build())
            .setOngoing(true)
            .build()
    }
}
