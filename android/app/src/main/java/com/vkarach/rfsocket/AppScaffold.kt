package com.vkarach.rfsocket

import androidx.annotation.DrawableRes
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.consumeWindowInsets
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource

private enum class Tab(val label: String, @DrawableRes val icon: Int) {
    Socket("Socket", R.drawable.ic_power),
    Clips("Clips", R.drawable.ic_clips),
}

@Composable
fun AppScaffold(client: SocketClient, channel: String) {
    var tab by rememberSaveable { mutableStateOf(Tab.Socket) }

    Scaffold(
        containerColor = Palette.Background,
        // Screens draw under the status bar themselves; only the bottom bar's space is reserved here.
        contentWindowInsets = WindowInsets(0),
        bottomBar = {
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
        },
    ) { padding ->
        Box(modifier = Modifier.padding(padding).consumeWindowInsets(padding)) {
            when (tab) {
                Tab.Socket -> ToggleScreen(client = client, channel = channel)
                Tab.Clips -> ClipsScreen(client = client)
            }
        }
    }
}
