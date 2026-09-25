package com.vkarach.rfsocket

import android.graphics.Bitmap
import android.graphics.Color
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

const val FRAME_WIDTH = 128
const val FRAME_HEIGHT = 64
const val FRAME_SIZE = FRAME_WIDTH * FRAME_HEIGHT / 8

enum class ScaleMode { Fit, Fill }
enum class DitherMethod { Auto, Fs, Bayer, None }

private val BAYER_8 = intArrayOf(
    0, 32, 8, 40, 2, 34, 10, 42,
    48, 16, 56, 24, 50, 18, 58, 26,
    12, 44, 4, 36, 14, 46, 6, 38,
    60, 28, 52, 20, 62, 30, 54, 22,
    3, 35, 11, 43, 1, 33, 9, 41,
    51, 19, 59, 27, 49, 17, 57, 25,
    15, 47, 7, 39, 13, 45, 5, 37,
    63, 31, 55, 23, 61, 29, 53, 21,
)

// Mirrors convert.py's _BAYER_THRESHOLDS: (value + 0.5) * 255 / 64, tiled across the frame.
private val BAYER_THRESHOLDS = FloatArray(FRAME_WIDTH * FRAME_HEIGHT) { i ->
    val x = i % FRAME_WIDTH
    val y = i / FRAME_WIDTH
    (BAYER_8[(y % 8) * 8 + (x % 8)] + 0.5f) * 255f / 64f
}

/** `bits` is row-major (y * FRAME_WIDTH + x); output is MONO_VLSB, matching convert.pack_vlsb. */
fun packVlsb(bits: BooleanArray): ByteArray {
    require(bits.size == FRAME_WIDTH * FRAME_HEIGHT) { "bits must cover the full frame" }
    val out = ByteArray(FRAME_SIZE)
    for (page in 0 until FRAME_HEIGHT / 8) {
        for (x in 0 until FRAME_WIDTH) {
            var byte = 0
            for (i in 0 until 8) {
                if (bits[(page * 8 + i) * FRAME_WIDTH + x]) byte = byte or (1 shl i)
            }
            out[page * FRAME_WIDTH + x] = byte.toByte()
        }
    }
    return out
}

fun ditherBayer(gray: IntArray): BooleanArray = BooleanArray(gray.size) { gray[it] > BAYER_THRESHOLDS[it] }

fun ditherNone(gray: IntArray): BooleanArray = BooleanArray(gray.size) { gray[it] >= 128 }

/** Standard two-row-buffer Floyd-Steinberg; not guaranteed byte-identical to PIL's implementation. */
fun ditherFs(gray: IntArray): BooleanArray {
    val work = FloatArray(gray.size) { gray[it].toFloat() }
    val bits = BooleanArray(gray.size)
    for (y in 0 until FRAME_HEIGHT) {
        for (x in 0 until FRAME_WIDTH) {
            val i = y * FRAME_WIDTH + x
            val old = work[i]
            val new = if (old >= 128f) 255f else 0f
            bits[i] = new == 255f
            val err = old - new
            if (x + 1 < FRAME_WIDTH) work[i + 1] += err * 7 / 16
            if (y + 1 < FRAME_HEIGHT) {
                if (x > 0) work[i + FRAME_WIDTH - 1] += err * 3 / 16
                work[i + FRAME_WIDTH] += err * 5 / 16
                if (x + 1 < FRAME_WIDTH) work[i + FRAME_WIDTH + 1] += err * 1 / 16
            }
        }
    }
    return bits
}

private fun dither(gray: IntArray, method: DitherMethod): BooleanArray = when (method) {
    DitherMethod.Fs -> ditherFs(gray)
    DitherMethod.Bayer -> ditherBayer(gray)
    DitherMethod.None -> ditherNone(gray)
    DitherMethod.Auto -> throw IllegalArgumentException("resolve Auto before calling dither()")
}

/** Composites over black (alpha-aware) and applies Pillow's L = 0.299R + 0.587G + 0.114B. */
private fun luma(pixel: Int): Int {
    val a = Color.alpha(pixel) / 255f
    val r = Color.red(pixel) * a
    val g = Color.green(pixel) * a
    val b = Color.blue(pixel) * a
    return (r * 0.299f + g * 0.587f + b * 0.114f).roundToInt().coerceIn(0, 255)
}

/** Letterbox (Fit) or center-crop (Fill) into a FRAME_WIDTH x FRAME_HEIGHT gray array. */
fun scale(bitmap: Bitmap, mode: ScaleMode): IntArray {
    val srcW = bitmap.width
    val srcH = bitmap.height
    val gray = IntArray(FRAME_WIDTH * FRAME_HEIGHT)
    val scaleFactor = when (mode) {
        ScaleMode.Fit -> min(FRAME_WIDTH.toFloat() / srcW, FRAME_HEIGHT.toFloat() / srcH)
        ScaleMode.Fill -> max(FRAME_WIDTH.toFloat() / srcW, FRAME_HEIGHT.toFloat() / srcH)
    }
    val scaledW = (srcW * scaleFactor).roundToInt().coerceAtLeast(1)
    val scaledH = (srcH * scaleFactor).roundToInt().coerceAtLeast(1)
    val scaled = Bitmap.createScaledBitmap(bitmap, scaledW, scaledH, true)
    val offsetX = (FRAME_WIDTH - scaledW) / 2
    val offsetY = (FRAME_HEIGHT - scaledH) / 2
    for (y in 0 until FRAME_HEIGHT) {
        val sy = y - offsetY
        for (x in 0 until FRAME_WIDTH) {
            val sx = x - offsetX
            gray[y * FRAME_WIDTH + x] = if (sx in 0 until scaledW && sy in 0 until scaledH) {
                luma(scaled.getPixel(sx, sy))
            } else {
                0
            }
        }
    }
    if (scaled !== bitmap) scaled.recycle()
    return gray
}

fun toFrame(bitmap: Bitmap, mode: ScaleMode, ditherMethod: DitherMethod, invert: Boolean): ByteArray {
    val gray = scale(bitmap, mode)
    var bits = dither(gray, ditherMethod)
    if (invert) bits = BooleanArray(bits.size) { !bits[it] }
    return packVlsb(bits)
}
