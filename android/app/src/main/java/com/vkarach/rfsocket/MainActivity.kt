package com.vkarach.rfsocket

import android.graphics.Color
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory

private const val BASE_URL = "http://192.168.0.240"

class MainActivity : ComponentActivity() {

    private val model by viewModels<DeviceModel> {
        viewModelFactory { initializer { DeviceModel(SocketClient(BASE_URL)) } }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
        )
        super.onCreate(savedInstanceState)
        setContent {
            RfSocketTheme {
                AppScaffold(model = model)
            }
        }
    }
}
