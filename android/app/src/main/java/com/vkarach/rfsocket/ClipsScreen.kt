package com.vkarach.rfsocket

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.LifecycleResumeEffect
import java.io.IOException
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ClipsScreen(client: SocketClient) {
    var clips by remember { mutableStateOf<List<Clip>?>(null) }
    var starredOnly by rememberSaveable { mutableStateOf(false) }
    var refreshing by remember { mutableStateOf(false) }
    var pendingDelete by remember { mutableStateOf<Clip?>(null) }
    val snackbar = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    fun notify(message: String) {
        scope.launch { snackbar.showSnackbar(message) }
    }

    suspend fun refresh() {
        refreshing = true
        try {
            clips = client.clips()
        } catch (e: IOException) {
            notify("Device unreachable")
        } finally {
            refreshing = false
        }
    }

    fun act(action: suspend () -> Unit) {
        scope.launch {
            try {
                action()
            } catch (e: NotFoundException) {
                notify("Clip not found")
            } catch (e: IOException) {
                notify("Device unreachable")
                return@launch
            }
            refresh()
        }
    }

    LifecycleResumeEffect(Unit) {
        val job = scope.launch { refresh() }
        onPauseOrDispose { job.cancel() }
    }

    val playing = clips?.firstOrNull { it.playing }
    val visible = clips?.filter { !starredOnly || it.starred }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Brush.verticalGradient(listOf(Palette.BackgroundTop, Palette.Background)))
            .safeDrawingPadding(),
    ) {
        Text(
            text = "CLIPS",
            color = Palette.Muted,
            fontSize = 13.sp,
            letterSpacing = 3.sp,
            fontWeight = FontWeight.Medium,
            modifier = Modifier.padding(start = 20.dp, top = 20.dp),
        )
        SingleChoiceSegmentedButtonRow(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
        ) {
            listOf("All" to false, "Starred" to true).forEachIndexed { index, (label, starred) ->
                SegmentedButton(
                    selected = starredOnly == starred,
                    onClick = { starredOnly = starred },
                    shape = SegmentedButtonDefaults.itemShape(index, 2),
                    colors = SegmentedButtonDefaults.colors(
                        activeContainerColor = Palette.Amber,
                        activeContentColor = Palette.OnAmber,
                        inactiveContainerColor = Palette.Surface,
                        inactiveContentColor = Palette.Muted,
                        activeBorderColor = Palette.Amber,
                        inactiveBorderColor = Palette.Outline,
                    ),
                ) { Text(label) }
            }
        }
        PullToRefreshBox(
            isRefreshing = refreshing,
            onRefresh = { scope.launch { refresh() } },
            modifier = Modifier.weight(1f),
        ) {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 4.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                if (visible != null && visible.isEmpty()) {
                    item {
                        Text(
                            text = if (starredOnly) "No starred clips" else "No clips yet",
                            color = Palette.Muted,
                            fontSize = 15.sp,
                            modifier = Modifier
                                .fillParentMaxSize()
                                .padding(top = 48.dp),
                        )
                    }
                }
                items(visible.orEmpty(), key = { it.id }) { clip ->
                    ClipRow(
                        clip = clip,
                        onPlay = { once -> act { client.play(clip.id, once) } },
                        onStar = { act { client.star(clip.id, !clip.starred) } },
                        onDelete = { pendingDelete = clip },
                    )
                }
            }
        }
        if (playing != null) {
            NowPlaying(clip = playing, onStop = { act { client.stop() } })
        }
        SnackbarHost(snackbar)
    }

    pendingDelete?.let { clip ->
        AlertDialog(
            onDismissRequest = { pendingDelete = null },
            title = { Text("Delete clip?") },
            text = { Text(clip.name.ifEmpty { clip.id }) },
            confirmButton = {
                TextButton(onClick = {
                    pendingDelete = null
                    act { client.delete(clip.id) }
                }) { Text("Delete", color = Palette.Error) }
            },
            dismissButton = {
                TextButton(onClick = { pendingDelete = null }) { Text("Cancel") }
            },
            containerColor = Palette.Surface,
        )
    }
}

@Composable
private fun ClipRow(clip: Clip, onPlay: (once: Boolean) -> Unit, onStar: () -> Unit, onDelete: () -> Unit) {
    var menuOpen by remember { mutableStateOf(false) }
    val haptics = LocalHapticFeedback.current
    val shape = RoundedCornerShape(14.dp)

    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .clip(shape)
            .background(Palette.Surface)
            .border(1.dp, if (clip.playing) Palette.Amber else Palette.Outline, shape)
            .combinedClickable(
                onClick = { onPlay(false) },
                onLongClick = {
                    haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                    menuOpen = true
                },
            )
            .padding(start = 16.dp, top = 6.dp, bottom = 6.dp, end = 4.dp),
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = clip.name.ifEmpty { clip.id },
                color = if (clip.playing) Palette.Amber else Palette.Text,
                fontSize = 16.sp,
                fontWeight = FontWeight.Medium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Spacer(Modifier.height(2.dp))
            Text(
                text = "${clip.frames} frames - ${clip.sizeKb} KB",
                color = Palette.Muted,
                fontSize = 13.sp,
            )
        }
        IconButton(onClick = onStar) {
            Icon(
                painter = painterResource(if (clip.starred) R.drawable.ic_star else R.drawable.ic_star_outline),
                contentDescription = if (clip.starred) "Unstar" else "Star",
                tint = if (clip.starred) Palette.Amber else Palette.Muted,
            )
        }
        Box {
            IconButton(onClick = { menuOpen = true }) {
                Icon(painterResource(R.drawable.ic_more), contentDescription = "More", tint = Palette.Muted)
            }
            DropdownMenu(
                expanded = menuOpen,
                onDismissRequest = { menuOpen = false },
                containerColor = Palette.Surface,
            ) {
                DropdownMenuItem(
                    text = { Text("Play once") },
                    onClick = {
                        menuOpen = false
                        onPlay(true)
                    },
                )
                DropdownMenuItem(
                    text = { Text("Delete", color = Palette.Error) },
                    onClick = {
                        menuOpen = false
                        onDelete()
                    },
                )
            }
        }
    }
}

@Composable
private fun NowPlaying(clip: Clip, onStop: () -> Unit) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 8.dp)
            .clip(RoundedCornerShape(14.dp))
            .background(Brush.linearGradient(listOf(Palette.Amber, Palette.Orange)))
            .padding(start = 16.dp, end = 4.dp),
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text("NOW PLAYING", color = Palette.OnAmber, fontSize = 11.sp, letterSpacing = 2.sp)
            Text(
                text = clip.name.ifEmpty { clip.id },
                color = Palette.OnAmber,
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        Spacer(Modifier.width(8.dp))
        IconButton(onClick = onStop) {
            Icon(painterResource(R.drawable.ic_stop), contentDescription = "Stop", tint = Palette.OnAmber)
        }
    }
}
