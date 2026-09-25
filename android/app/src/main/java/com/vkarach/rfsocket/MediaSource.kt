package com.vkarach.rfsocket

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import android.net.Uri
import com.bumptech.glide.gifdecoder.GifDecoder
import com.bumptech.glide.gifdecoder.GifHeaderParser
import com.bumptech.glide.gifdecoder.StandardGifDecoder

// A GIF delay of 10ms or less is treated as unset, same as browsers and host/sources.py.
private const val MIN_GIF_DELAY_MS = 10
private const val DEFAULT_FRAME_DURATION_MS = 100
private const val DECODE_TIMEOUT_US = 10_000L

sealed interface MediaSource {
    /** Bitmap ownership passes to the caller; recycle it after conversion. */
    fun frames(): Sequence<Pair<Bitmap, Int>>
}

class ImageSource(private val bitmap: Bitmap) : MediaSource {
    override fun frames(): Sequence<Pair<Bitmap, Int>> = sequenceOf(bitmap to 0)
}

private class SimpleBitmapProvider : GifDecoder.BitmapProvider {
    override fun obtain(width: Int, height: Int, config: Bitmap.Config) = Bitmap.createBitmap(width, height, config)
    override fun release(bitmap: Bitmap) {}
    override fun obtainByteArray(size: Int) = ByteArray(size)
    override fun release(bytes: ByteArray) {}
    override fun obtainIntArray(size: Int) = IntArray(size)
    override fun release(array: IntArray) {}
}

class GifSource(private val bytes: ByteArray) : MediaSource {
    override fun frames(): Sequence<Pair<Bitmap, Int>> = sequence {
        val buffer = java.nio.ByteBuffer.wrap(bytes)
        val header = GifHeaderParser().setData(buffer).parseHeader()
        val decoder = StandardGifDecoder(SimpleBitmapProvider(), header, buffer)
        decoder.advance()
        var index = 0
        while (index < decoder.frameCount) {
            val bitmap = decoder.nextFrame ?: break
            val delayMs = decoder.getDelay(index)
            yield(bitmap to if (delayMs <= MIN_GIF_DELAY_MS) DEFAULT_FRAME_DURATION_MS else delayMs)
            decoder.advance()
            index++
        }
    }
}

class VideoSource(private val context: Context, private val uri: Uri) : MediaSource {
    override fun frames(): Sequence<Pair<Bitmap, Int>> = sequence {
        val extractor = MediaExtractor()
        extractor.setDataSource(context, uri, null)
        val trackIndex = (0 until extractor.trackCount).firstOrNull {
            extractor.getTrackFormat(it).getString(MediaFormat.KEY_MIME)?.startsWith("video/") == true
        } ?: throw IllegalArgumentException("no video track")
        extractor.selectTrack(trackIndex)
        val format = extractor.getTrackFormat(trackIndex)
        val frameDurationMs = if (format.containsKey(MediaFormat.KEY_FRAME_RATE)) {
            (1000f / format.getInteger(MediaFormat.KEY_FRAME_RATE)).toInt().coerceAtLeast(1)
        } else {
            DEFAULT_FRAME_DURATION_MS
        }
        val mime = format.getString(MediaFormat.KEY_MIME)!!
        val codec = MediaCodec.createDecoderByType(mime)
        codec.configure(format, null, null, 0)
        codec.start()
        try {
            var inputDone = false
            while (true) {
                if (!inputDone) {
                    val inIndex = codec.dequeueInputBuffer(DECODE_TIMEOUT_US)
                    if (inIndex >= 0) {
                        val buffer = codec.getInputBuffer(inIndex)!!
                        val sampleSize = extractor.readSampleData(buffer, 0)
                        if (sampleSize < 0) {
                            codec.queueInputBuffer(inIndex, 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
                            inputDone = true
                        } else {
                            codec.queueInputBuffer(inIndex, 0, sampleSize, extractor.sampleTime, 0)
                            extractor.advance()
                        }
                    }
                }
                val info = MediaCodec.BufferInfo()
                val outIndex = codec.dequeueOutputBuffer(info, DECODE_TIMEOUT_US)
                if (outIndex >= 0) {
                    val image = codec.getOutputImage(outIndex)
                    if (image != null) {
                        yield(yPlaneToBitmap(image) to frameDurationMs)
                        image.close()
                    }
                    codec.releaseOutputBuffer(outIndex, false)
                    if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) break
                } else if (outIndex == MediaCodec.INFO_TRY_AGAIN_LATER && inputDone) {
                    break
                }
            }
        } finally {
            codec.stop()
            codec.release()
            extractor.release()
        }
    }

    private fun yPlaneToBitmap(image: android.media.Image): Bitmap {
        val plane = image.planes[0]
        val bitmap = Bitmap.createBitmap(image.width, image.height, Bitmap.Config.ALPHA_8)
        val rowStride = plane.rowStride
        val buffer = plane.buffer
        val row = ByteArray(image.width)
        for (y in 0 until image.height) {
            buffer.position(y * rowStride)
            buffer.get(row, 0, image.width)
            bitmap.setPixels(
                IntArray(image.width) { x ->
                    (row[x].toInt() and 0xFF).let { 0xFF shl 24 or (it shl 16) or (it shl 8) or it }
                },
                0, image.width, 0, y, image.width, 1,
            )
        }
        return bitmap
    }
}

fun openMediaSource(context: Context, uri: Uri, mimeType: String?): MediaSource {
    return when {
        mimeType == "image/gif" -> GifSource(
            context.contentResolver.openInputStream(uri)?.use { it.readBytes() }
                ?: throw IllegalArgumentException("cannot read $uri"),
        )
        mimeType?.startsWith("video/") == true -> VideoSource(context, uri)
        mimeType?.startsWith("image/") == true -> {
            val bitmap = context.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it) }
                ?: throw IllegalArgumentException("cannot decode $uri")
            ImageSource(bitmap)
        }
        else -> throw IllegalArgumentException("unsupported media type: $mimeType")
    }
}
