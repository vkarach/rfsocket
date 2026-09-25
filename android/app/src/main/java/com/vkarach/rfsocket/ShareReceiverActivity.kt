package com.vkarach.rfsocket

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle

class ShareReceiverActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val uri = intent.getParcelableExtra<Uri>(Intent.EXTRA_STREAM)
        if (uri != null) {
            val settings = loadStreamSettings(applicationContext)
            StreamController.start(
                applicationContext, uri, intent.type, uri.lastPathSegment ?: "shared",
                DEVICE_HOST, DEVICE_STREAM_PORT, settings,
            )
        }
        startActivity(Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        finish()
    }
}
