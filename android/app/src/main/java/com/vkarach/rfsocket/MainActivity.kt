package com.vkarach.rfsocket

import android.graphics.Color
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge

private const val BASE_URL = "http://192.168.0.240"
private const val CHANNEL = "a"

class MainActivity : ComponentActivity() {

    private val client = SocketClient(BASE_URL)

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
        )
        super.onCreate(savedInstanceState)
        setContent {
            RfSocketTheme {
                ToggleScreen(client = client, channel = CHANNEL)
            }
        }
    }
}
