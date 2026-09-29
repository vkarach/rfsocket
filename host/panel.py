import argparse
import ctypes
import os
import subprocess
import sys
import urllib.error
import urllib.request
import webbrowser

import webview

GITHUB_URL = "https://github.com/vkarach/rfsocket"

PORT = 80
TIMEOUT_S = 3
HERE = os.path.dirname(os.path.abspath(__file__))
OLED_SCRIPT = os.path.join(HERE, "oled.py")
ICON_PATH = os.path.join(HERE, "panel.ico")
APP_ID = "vkarach.rfsocket.panel"
MEDIA_FILE_TYPES = ("Media (*.jpg;*.jpeg;*.png;*.bmp;*.gif;*.mp4;*.mov;*.mkv;*.avi;*.webm)", "All files (*.*)")


class DeviceError(Exception):
    pass


class Api:
    def __init__(self, host):
        self.base_url = "http://%s:%d" % (host, PORT)
        self.host = host

    def _get(self, path):
        try:
            with urllib.request.urlopen(self.base_url + path, timeout=TIMEOUT_S) as resp:
                return resp.read().decode().strip()
        except (urllib.error.URLError, OSError) as exc:
            raise DeviceError(str(exc))

    def state(self):
        try:
            channels = dict(pair.split(":") for pair in self._get("/state").split())
            screen = self._get("/screen")
            brightness = int(self._get("/brightness"))
            return {"ok": True, "channels": channels, "screen": screen, "brightness": brightness, "host": self.host}
        except DeviceError as exc:
            return {"ok": False, "error": str(exc)}

    def toggle(self, channel):
        try:
            return {"ok": True, "state": self._get("/%s/toggle" % channel)}
        except DeviceError as exc:
            return {"ok": False, "error": str(exc)}

    def pin_screen(self, mode):
        try:
            self._get("/screen/%s" % mode)
            return {"ok": True}
        except DeviceError as exc:
            return {"ok": False, "error": str(exc)}

    def set_brightness(self, value):
        try:
            self._get("/brightness/%d" % int(value))
            return {"ok": True}
        except DeviceError as exc:
            return {"ok": False, "error": str(exc)}

    def list_clips(self):
        try:
            raw = self._get("/clips")
            clips = []
            for line in raw.splitlines():
                if not line.strip():
                    continue
                parts = line.split(" ", 5)
                if len(parts) < 6:
                    continue
                clip_id, frames, size_kb, star, playing, name = parts
                clips.append({
                    "id": clip_id,
                    "frames": int(frames),
                    "size_kb": int(size_kb),
                    "star": star == "*",
                    "playing": playing == ">",
                    "name": name,
                })
            return {"ok": True, "clips": clips}
        except DeviceError as exc:
            return {"ok": False, "error": str(exc)}

    def play_clip(self, clip_id, once):
        try:
            path = "/clips/%s/play" % clip_id
            if once:
                path += "?once"
            self._get(path)
            return {"ok": True}
        except DeviceError as exc:
            return {"ok": False, "error": str(exc)}

    def stop_clip(self):
        try:
            self._get("/clips/stop")
            return {"ok": True}
        except DeviceError as exc:
            return {"ok": False, "error": str(exc)}

    def star_clip(self, clip_id, star):
        try:
            self._get("/clips/%s/%s" % (clip_id, "star" if star else "unstar"))
            return {"ok": True}
        except DeviceError as exc:
            return {"ok": False, "error": str(exc)}

    def delete_clip(self, clip_id):
        try:
            self._get("/clips/%s/delete" % clip_id)
            return {"ok": True}
        except DeviceError as exc:
            return {"ok": False, "error": str(exc)}

    def browse_file(self):
        result = webview.windows[0].create_file_dialog(webview.OPEN_DIALOG, file_types=MEDIA_FILE_TYPES)
        return result[0] if result else None

    def stream(self, path, loop, keep, scale, invert, dither):
        args = [sys.executable, OLED_SCRIPT, path, "--host", self.host, "--" + scale]
        if loop:
            args.append("--loop")
        if keep:
            args.append("--keep")
        if invert:
            args.append("--invert")
        if dither != "auto":
            args += ["--dither", dither]
        subprocess.Popen(args, creationflags=subprocess.CREATE_NO_WINDOW)
        return {"ok": True}

    def open_github(self):
        webbrowser.open(GITHUB_URL)


def parse_args(argv):
    parser = argparse.ArgumentParser(description="rfsocket control panel")
    parser.add_argument("--host", default=os.environ.get("RFSOCKET_HOST"), required=not os.environ.get("RFSOCKET_HOST"))
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    api = Api(args.host)
    # Without its own app id the taskbar groups the window under python and shows the python icon.
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    webview.create_window("rfsocket", os.path.join(HERE, "panel.html"), width=360, height=524, resizable=False,
                          background_color="#0E1116", js_api=api)
    webview.start(icon=ICON_PATH)


if __name__ == "__main__":
    main(sys.argv[1:])
