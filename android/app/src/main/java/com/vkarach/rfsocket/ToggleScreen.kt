package com.vkarach.rfsocket

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
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
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.LifecycleResumeEffect
import java.io.IOException
import kotlinx.coroutines.launch

@Composable
fun ToggleScreen(client: SocketClient, channel: String) {
    var isOn by remember { mutableStateOf<Boolean?>(null) }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()
    val haptics = LocalHapticFeedback.current

    suspend fun sync(request: suspend () -> Boolean) {
        busy = true
        try {
            isOn = request()
            error = null
        } catch (e: IOException) {
            error = "Device unreachable"
        } finally {
            busy = false
        }
    }

    LifecycleResumeEffect(channel) {
        val refresh = scope.launch { sync { client.state(channel) } }
        onPauseOrDispose { refresh.cancel() }
    }

    val on = isOn == true
    val glowAlpha by animateFloatAsState(if (on) 0.35f else 0f, tween(500), label = "glow")

    Box(
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
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = "CHANNEL ${channel.uppercase()}",
                color = Palette.Muted,
                fontSize = 13.sp,
                letterSpacing = 3.sp,
                fontWeight = FontWeight.Medium,
            )
            Spacer(Modifier.height(40.dp))
            PowerButton(
                on = on,
                busy = busy,
                onClick = {
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    scope.launch { sync { client.toggle(channel) } }
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
            Spacer(Modifier.height(12.dp))
            Text(
                text = error ?: " ",
                color = Palette.Error,
                fontSize = 14.sp,
            )
        }
    }
}

@Composable
private fun PowerButton(on: Boolean, busy: Boolean, onClick: () -> Unit) {
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
                    enabled = !busy,
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
