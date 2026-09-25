# rfsocket

ESP32-based RF power socket controller with an SSD1306 OLED. The device switches RF outlets over
HTTP and doubles as a small display: it streams images, GIFs and video from a PC or an Android
phone, keeps a local history of streamed clips, and shows a status screen or a clock when idle.

## Repository layout

- `device/` - MicroPython firmware (`main.py` + `device/lib/`). Runs on the ESP32.
- `host/` - PC-side streaming client (`host/oled.py`) and its supporting modules
  (decoding/conversion, the frame/STORE protocol, clip building).
- `android/` - the Android app: channel control, clip history, and phone-side streaming.
- `tests/device/` - portable pieces of `device/lib/` tested on CPython (see `tests/device/conftest.py`).
- `docs/superpowers/` - design specs and implementation plans (git-ignored; local working notes).

## Device setup

1. Flash `ESP32_GENERIC-20260824-v1.29.0.bin` (MicroPython) to the board.
2. Copy `config.example.py` to `device/config.py` and fill in Wi-Fi credentials, static IP, RF
   channel codes, and the clip-history budget (`CLIP_BUDGET`, `CLIP_MAX_COUNT`, `CLIP_AUTO_MAX`).
   `device/config.py` is git-ignored - it holds secrets.
3. Upload `device/main.py` and everything under `device/lib/` to the board.

## PC streaming client

```
pip install -r host/requirements.txt
python host/oled.py --host <device-ip> <image-or-gif-or-video>
```

Requires `ffmpeg`/`ffprobe` on PATH for video. See `python host/oled.py --help` for scaling,
dithering, looping and history (`--keep`) options.

## Android app

Open `android/` in Android Studio, or build from the command line:

```
android\gradlew.bat -p android testDebugUnitTest assembleDebug
```

The device address is a constant in `android/app/src/main/java/com/vkarach/rfsocket/DeviceConfig.kt`.

## Testing

```
.venv/Scripts/python.exe -m pytest host/tests tests/device -q
android\gradlew.bat -p android testDebugUnitTest
```
