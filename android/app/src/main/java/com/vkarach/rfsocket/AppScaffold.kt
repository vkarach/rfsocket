package com.vkarach.rfsocket

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.annotation.DrawableRes
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.consumeWindowInsets
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle

private enum class Tab(val label: String, @DrawableRes val icon: Int) {
    Socket("Socket", R.drawable.ic_power),
    Clips("Clips", R.drawable.ic_clips),
}

@Composable
fun AppScaffold(model: DeviceModel) {
    var tab by rememberSaveable { mutableStateOf(Tab.Socket) }
    val state by model.state.collectAsStateWithLifecycle()
    val activeStream by StreamController.active.collectAsStateWithLifecycle()
    var showPanel by remember { mutableStateOf(false) }
    val context = LocalContext.current
    val snackbar = remember { SnackbarHostState() }

    LifecycleResumeEffect(model) {
        model.startPolling()
        onPauseOrDispose { model.stopPolling() }
    }

    LaunchedEffect(Unit) {
        StreamController.outcome.collect { snackbar.showSnackbar(it) }
    }

    val pickMedia = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        if (uri != null) {
            val mimeType = context.contentResolver.getType(uri)
            StreamController.start(
                context, uri, mimeType, uri.lastPathSegment ?: "picked",
                DEVICE_HOST, DEVICE_STREAM_PORT, loadStreamSettings(context),
            )
        }
    }

    Scaffold(
        containerColor = Palette.Background,
        // Screens draw under the status bar themselves; only the bars' space is reserved here.
        contentWindowInsets = WindowInsets(0),
        topBar = {
            if (state.reachable == false) {
                UnreachableBanner()
            }
        },
        snackbarHost = { SnackbarHost(snackbar) },
        bottomBar = {
            Column {
                activeStream?.let { stream ->
                    StreamingBar(
                        name = stream.name,
                        onEdit = { showPanel = true },
                        onStop = { StreamController.stop() },
                    )
                }
                NavigationBar(containerColor = Palette.Surface) {
                    Tab.entries.forEach { entry ->
                        NavigationBarItem(
                            selected = tab == entry,
                            onClick = { tab = entry },
                            icon = { Icon(painterResource(entry.icon), contentDescription = null) },
                            label = { Text(entry.label) },
                            colors = NavigationBarItemDefaults.colors(
                                selectedIconColor = Palette.OnAmber,
                                selectedTextColor = Palette.Amber,
                                indicatorColor = Palette.Amber,
                                unselectedIconColor = Palette.Muted,
                                unselectedTextColor = Palette.Muted,
                            ),
                        )
                    }
                }
            }
        },
    ) { padding ->
        Box(modifier = Modifier.padding(padding).consumeWindowInsets(padding)) {
            when (tab) {
                Tab.Socket -> SocketScreen(model = model, state = state)
                Tab.Clips -> ClipsScreen(
                    model = model,
                    state = state,
                    onPickFile = {
                        pickMedia.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageAndVideo))
                    },
                )
            }
        }
    }

    activeStream?.let { stream ->
        if (showPanel) {
            StreamPanel(
                state = stream,
                onSettings = { StreamController.updateSettings(it) },
                onDismiss = { showPanel = false },
            )
        }
    }
}

@Composable
private fun StreamingBar(name: String, onEdit: () -> Unit, onStop: () -> Unit) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .background(Palette.Surface)
            .padding(start = 16.dp, end = 4.dp, top = 8.dp, bottom = 8.dp),
    ) {
        Text(
            text = "Streaming $name",
            color = Palette.Text,
            fontSize = 15.sp,
            fontWeight = FontWeight.Medium,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f),
        )
        IconButton(onClick = onEdit) {
            Icon(painterResource(R.drawable.ic_edit), contentDescription = "Stream settings", tint = Palette.Amber)
        }
        IconButton(onClick = onStop) {
            Icon(painterResource(R.drawable.ic_stop), contentDescription = "Stop", tint = Palette.Error)
        }
    }
}

@Composable
private fun UnreachableBanner() {
    Text(
        text = "Device unreachable - retrying",
        color = Palette.Error,
        fontSize = 14.sp,
        fontWeight = FontWeight.Medium,
        modifier = Modifier
            .fillMaxWidth()
            .background(Palette.Surface)
            .statusBarsPadding()
            .padding(horizontal = 20.dp, vertical = 10.dp),
    )
}
