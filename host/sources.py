import json
import os
import subprocess
from fractions import Fraction

from PIL import Image, ImageSequence, UnidentifiedImageError

from protocol import HEIGHT, WIDTH

DEFAULT_FRAME_DURATION = 0.1
# Browsers treat GIF delays of 10 ms or less as unset.
MIN_GIF_DURATION_MS = 10
VIDEO_MAX_SHORT_SIDE = 2 * min(WIDTH, HEIGHT)


class SourceError(Exception):
    pass


class ImageSource:
    kind = "image"

    def __init__(self, path):
        self.path = path

    def frames(self):
        with Image.open(self.path) as img:
            yield img.copy(), 0


class GifSource:
    kind = "gif"

    def __init__(self, path):
        self.path = path

    def frames(self):
        with Image.open(self.path) as img:
            for frame in ImageSequence.Iterator(img):
                duration_ms = frame.info.get("duration") or 0
                if duration_ms <= MIN_GIF_DURATION_MS:
                    duration = DEFAULT_FRAME_DURATION
                else:
                    duration = duration_ms / 1000
                yield frame.convert("RGBA"), duration


class VideoSource:
    kind = "video"

    def __init__(self, path, width, height, fps):
        self.path = path
        self.fps = fps
        self.size = _video_output_size(width, height)

    def frames(self):
        width, height = self.size
        frame_bytes = width * height
        try:
            proc = subprocess.Popen(
                ["ffmpeg", "-v", "error", "-i", self.path, "-an",
                 "-vf", "scale=%d:%d" % (width, height),
                 "-pix_fmt", "gray", "-f", "rawvideo", "-"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            raise SourceError("ffmpeg not found on PATH")
        try:
            while True:
                data = proc.stdout.read(frame_bytes)
                if len(data) < frame_bytes:
                    return
                yield Image.frombytes("L", (width, height), data), 1 / self.fps
        finally:
            proc.kill()
            proc.wait()
            proc.stdout.close()


def _video_output_size(width, height):
    short = min(width, height)
    factor = min(1, VIDEO_MAX_SHORT_SIDE / short)
    return max(2, round(width * factor / 2) * 2), max(2, round(height * factor / 2) * 2)


def _probe_video(path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,avg_frame_rate,r_frame_rate",
             "-of", "json", path],
            capture_output=True, text=True)
    except FileNotFoundError:
        raise SourceError("ffprobe not found on PATH")
    streams = json.loads(result.stdout or "{}").get("streams") if result.returncode == 0 else None
    if not streams:
        raise SourceError("unsupported or unreadable media: %s" % path)
    stream = streams[0]
    for key in ("avg_frame_rate", "r_frame_rate"):
        rate = stream.get(key, "0/0")
        if not rate.endswith("/0") and Fraction(rate) > 0:
            return stream["width"], stream["height"], float(Fraction(rate))
    raise SourceError("cannot determine frame rate: %s" % path)


def open_source(path):
    if not os.path.isfile(path):
        raise SourceError("file not found: %s" % path)
    try:
        with Image.open(path) as img:
            animated = getattr(img, "n_frames", 1) > 1
        return GifSource(path) if animated else ImageSource(path)
    except UnidentifiedImageError:
        pass
    return VideoSource(path, *_probe_video(path))
