package com.vkarach.rfsocket

import android.content.Context
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch

private const val PREFS = "rfsocket"
private const val PREF_CHANNEL = "channel"

@Composable
fun SocketScreen(model: DeviceModel, state: DeviceState) {
    val prefs = LocalContext.current.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    var chosen by remember { mutableStateOf(prefs.getString(PREF_CHANNEL, null)) }
    var busy by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val haptics = LocalHapticFeedback.current

    val states = state.channels
    // A remembered channel the device no longer reports falls back to its first one.
    val channel = states?.keys?.let { names -> chosen?.takeIf { it in names } ?: names.firstOrNull() }
    val isOn = channel?.let { states[it] }

    val glowAlpha by animateFloatAsState(if (isOn == true) 0.35f else 0f, tween(500), label = "glow")

    BoxWithConstraints(
        modifier = Modifier
            .fillMaxSize()
            .background(Brush.verticalGradient(listOf(Palette.BackgroundTop, Palette.Background)))
            .background(
                Brush.radialGradient(
                    listOf(Palette.Amber.copy(alpha = glowAlpha), Color.Transparent),
                    radius = 900f,
                )
            )
            .safeDrawingPadding(),
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier
                .verticalScroll(rememberScrollState())
                .fillMaxWidth()
                .heightIn(min = maxHeight),
        ) {
            ChannelPicker(
                channel = channel,
                states = states.orEmpty(),
                onPick = {
                    chosen = it
                    prefs.edit().putString(PREF_CHANNEL, it).apply()
                },
            )
            Spacer(Modifier.height(40.dp))
            PowerButton(
                on = isOn == true,
                busy = busy,
                enabled = channel != null,
                onClick = {
                    val target = channel ?: return@PowerButton
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    scope.launch {
                        busy = true
                        try {
                            model.setChannel(target, isOn != true).join()
                        } finally {
                            busy = false
                        }
                    }
                },
            )
            Spacer(Modifier.height(40.dp))
            Text(
                text = when (isOn) {
                    true -> "On"
                    false -> "Off"
                    null -> "--"
                },
                color = Palette.Text,
                fontSize = 34.sp,
                fontWeight = FontWeight.SemiBold,
            )
            Spacer(Modifier.height(44.dp))
            ScreenPicker(selected = state.screen, onPick = { model.pinScreen(it) })
        }
    }
}

@Composable
private fun ChannelPicker(channel: String?, states: Map<String, Boolean>, onPick: (String) -> Unit) {
    var open by remember { mutableStateOf(false) }

    Box {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .clip(RoundedCornerShape(8.dp))
                .clickable(enabled = states.isNotEmpty()) { open = true }
                .padding(start = 12.dp, end = 4.dp, top = 4.dp, bottom = 4.dp),
        ) {
            Text(
                text = "CHANNEL ${channel?.uppercase() ?: "--"}",
                color = Palette.Muted,
                fontSize = 13.sp,
                letterSpacing = 3.sp,
                fontWeight = FontWeight.Medium,
            )
            Icon(painterResource(R.drawable.ic_arrow_drop_down), contentDescription = "Choose channel", tint = Palette.Muted)
        }
        DropdownMenu(expanded = open, onDismissRequest = { open = false }, containerColor = Palette.Surface) {
            states.forEach { (name, on) ->
                DropdownMenuItem(
                    text = {
                        Text(
                            text = name.uppercase(),
                            color = if (name == channel) Palette.Amber else Palette.Text,
                            fontWeight = FontWeight.Medium,
                        )
                    },
                    trailingIcon = {
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .clip(CircleShape)
                                .background(if (on) Palette.Amber else Palette.Outline),
                        )
                    },
                    onClick = {
                        open = false
                        onPick(name)
                    },
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ScreenPicker(selected: ScreenMode?, onPick: (ScreenMode) -> Unit) {
    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(horizontal = 24.dp)) {
        Text(
            text = "SCREEN",
            color = Palette.Muted,
            fontSize = 13.sp,
            letterSpacing = 3.sp,
            fontWeight = FontWeight.Medium,
        )
        Spacer(Modifier.height(12.dp))
        SingleChoiceSegmentedButtonRow(modifier = Modifier.fillMaxWidth()) {
            ScreenMode.entries.forEachIndexed { index, mode ->
                SegmentedButton(
                    selected = selected == mode,
                    onClick = { onPick(mode) },
                    shape = SegmentedButtonDefaults.itemShape(index, ScreenMode.entries.size),
                    colors = SegmentedButtonDefaults.colors(
                        activeContainerColor = Palette.Amber,
                        activeContentColor = Palette.OnAmber,
                        inactiveContainerColor = Palette.Surface,
                        inactiveContentColor = Palette.Muted,
                        activeBorderColor = Palette.Amber,
                        inactiveBorderColor = Palette.Outline,
                    ),
                ) { Text(mode.label) }
            }
        }
    }
}

@Composable
private fun PowerButton(on: Boolean, busy: Boolean, enabled: Boolean, onClick: () -> Unit) {
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val scale by animateFloatAsState(if (pressed) 0.93f else 1f, label = "scale")
    val top by animateColorAsState(if (on) Palette.Amber else Palette.Surface, tween(400), label = "top")
    val bottom by animateColorAsState(if (on) Palette.Orange else Palette.Background, tween(400), label = "bottom")
    val iconTint by animateColorAsState(if (on) Palette.OnAmber else Palette.Muted, tween(400), label = "icon")
    val border by animateColorAsState(if (on) Palette.Amber else Palette.Outline, tween(400), label = "border")

    Box(contentAlignment = Alignment.Center, modifier = Modifier.size(232.dp)) {
        if (busy) {
            CircularProgressIndicator(
                modifier = Modifier.fillMaxSize(),
                color = Palette.Amber,
                strokeWidth = 3.dp,
                trackColor = Color.Transparent,
            )
        }
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .padding(16.dp)
                .fillMaxSize()
                .scale(scale)
                .clip(CircleShape)
                .background(Brush.linearGradient(listOf(top, bottom)))
                .border(1.dp, border, CircleShape)
                .clickable(
                    interactionSource = interaction,
                    indication = null,
                    enabled = enabled && !busy,
                    onClick = onClick,
                ),
        ) {
            Icon(
                painter = painterResource(R.drawable.ic_power),
                contentDescription = if (on) "Turn off" else "Turn on",
                tint = iconTint,
                modifier = Modifier.size(84.dp),
            )
        }
    }
}
