package com.vkarach.rfsocket

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color as AndroidColor
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private const val PREFS = "rfsocket"

fun loadStreamSettings(context: Context): StreamSettings {
    val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    return StreamSettings(
        scaleMode = ScaleMode.entries.getOrElse(prefs.getInt("scale", 0)) { ScaleMode.Fit },
        dither = DitherMethod.entries.getOrElse(prefs.getInt("dither", 0)) { DitherMethod.Auto },
        invert = prefs.getBoolean("invert", false),
        loop = prefs.getBoolean("loop", true),
        star = prefs.getBoolean("star", false),
    )
}

fun saveStreamSettings(context: Context, settings: StreamSettings) {
    context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
        .putInt("scale", settings.scaleMode.ordinal)
        .putInt("dither", settings.dither.ordinal)
        .putBoolean("invert", settings.invert)
        .putBoolean("loop", settings.loop)
        .putBoolean("star", settings.star)
        .apply()
}

private fun frameToBitmap(frame: ByteArray): Bitmap {
    val bitmap = Bitmap.createBitmap(FRAME_WIDTH, FRAME_HEIGHT, Bitmap.Config.ARGB_8888)
    for (page in 0 until FRAME_HEIGHT / 8) {
        for (x in 0 until FRAME_WIDTH) {
            val byte = frame[page * FRAME_WIDTH + x].toInt()
            for (bit in 0 until 8) {
                val on = (byte shr bit) and 1 == 1
                bitmap.setPixel(x, page * 8 + bit, if (on) AndroidColor.WHITE else AndroidColor.BLACK)
            }
        }
    }
    return bitmap
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StreamPanel(state: StreamState, onSettings: (StreamSettings) -> Unit, onDismiss: () -> Unit) {
    val context = LocalContext.current

    ModalBottomSheet(onDismissRequest = onDismiss, containerColor = Palette.Surface) {
        Column(modifier = Modifier.padding(20.dp)) {
            val bitmap = remember(state.previewFrame) { frameToBitmap(state.previewFrame) }
            Canvas(
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(FRAME_WIDTH.toFloat() / FRAME_HEIGHT)
                    .clip(RoundedCornerShape(8.dp))
                    .background(Color.Black),
            ) {
                drawImage(image = bitmap.asImageBitmap(), dstSize = IntSize(size.width.toInt(), size.height.toInt()))
            }
            Spacer(Modifier.height(20.dp))

            fun update(next: StreamSettings) {
                saveStreamSettings(context, next)
                onSettings(next)
            }

            SettingRow("SCALE") {
                SingleChoiceSegmentedButtonRow(modifier = Modifier.fillMaxWidth()) {
                    ScaleMode.entries.forEachIndexed { index, mode ->
                        SegmentedButton(
                            selected = state.settings.scaleMode == mode,
                            onClick = { update(state.settings.copy(scaleMode = mode)) },
                            shape = SegmentedButtonDefaults.itemShape(index, ScaleMode.entries.size),
                        ) { Text(mode.name) }
                    }
                }
            }
            SettingRow("DITHER") {
                SingleChoiceSegmentedButtonRow(modifier = Modifier.fillMaxWidth()) {
                    DitherMethod.entries.forEachIndexed { index, method ->
                        SegmentedButton(
                            selected = state.settings.dither == method,
                            onClick = { update(state.settings.copy(dither = method)) },
                            shape = SegmentedButtonDefaults.itemShape(index, DitherMethod.entries.size),
                        ) { Text(method.name) }
                    }
                }
            }
            ToggleRow("Invert", state.settings.invert) { update(state.settings.copy(invert = it)) }
            ToggleRow("Loop", state.settings.loop) { update(state.settings.copy(loop = it)) }
            ToggleRow("Star (keep in history)", state.settings.star) { update(state.settings.copy(star = it)) }
        }
    }
}

@Composable
private fun SettingRow(label: String, content: @Composable () -> Unit) {
    Column(modifier = Modifier.padding(vertical = 8.dp)) {
        Text(text = label, color = Palette.Muted, fontSize = 12.sp, letterSpacing = 2.sp)
        Spacer(Modifier.height(6.dp))
        content()
    }
}

@Composable
private fun ToggleRow(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
    ) {
        Text(text = label, color = Palette.Text, fontSize = 15.sp, modifier = Modifier.weight(1f))
        Switch(
            checked = checked,
            onCheckedChange = onChange,
            colors = SwitchDefaults.colors(checkedTrackColor = Palette.Amber),
        )
    }
}
