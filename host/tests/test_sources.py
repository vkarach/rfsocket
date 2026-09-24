import shutil
import subprocess

import pytest
from PIL import Image

import sources

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not on PATH")


def make_gif(path, durations, transparent=False):
    frames = []
    for i in range(len(durations)):
        frame = Image.new("P", (30, 20), i)
        frame.putpalette([0, 0, 0, 255, 0, 0, 0, 255, 0, 0, 0, 255])
        frames.append(frame)
    options = {"transparency": 0} if transparent else {}
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, disposal=2, **options)
    return path


def make_video(path, seconds=1, rate=10, size="320x240"):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                    "-i", "testsrc=duration=%d:size=%s:rate=%d" % (seconds, size, rate),
                    "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def test_png_is_single_frame_image(tmp_path):
    path = tmp_path / "pic.png"
    Image.new("RGB", (50, 40), (10, 20, 30)).save(path)

    source = sources.open_source(str(path))
    frames = list(source.frames())

    assert source.kind == "image"
    assert len(frames) == 1
    assert frames[0][0].size == (50, 40)
    assert frames[0][1] == 0


def test_gif_durations_with_zero_defaulted(tmp_path):
    source = sources.open_source(str(make_gif(tmp_path / "anim.gif", [50, 0, 200])))

    durations = [duration for _, duration in source.frames()]

    assert source.kind == "gif"
    assert durations == pytest.approx([0.05, sources.DEFAULT_FRAME_DURATION, 0.2])


def test_gif_frames_can_be_replayed(tmp_path):
    source = sources.open_source(str(make_gif(tmp_path / "anim.gif", [100, 100])))

    assert len(list(source.frames())) == len(list(source.frames())) == 2


def test_transparent_gif_yields_full_canvas_rgba(tmp_path):
    source = sources.open_source(str(make_gif(tmp_path / "t.gif", [100, 100, 100], transparent=True)))

    for image, _ in source.frames():
        assert image.mode == "RGBA"
        assert image.size == (30, 20)


@needs_ffmpeg
def test_video_frames_and_durations(tmp_path):
    source = sources.open_source(str(make_video(tmp_path / "clip.mp4")))
    frames = list(source.frames())

    assert source.kind == "video"
    assert 9 <= len(frames) <= 11
    for image, duration in frames:
        assert duration == pytest.approx(0.1)
        assert min(image.size) <= sources.VIDEO_MAX_SHORT_SIDE
        assert image.size[0] / image.size[1] == pytest.approx(320 / 240, rel=0.05)


@needs_ffmpeg
def test_closing_video_iterator_stops_ffmpeg(tmp_path, monkeypatch):
    spawned = []
    real_popen = subprocess.Popen

    def spy(*args, **kwargs):
        proc = real_popen(*args, **kwargs)
        spawned.append(proc)
        return proc

    monkeypatch.setattr(sources.subprocess, "Popen", spy)
    source = sources.open_source(str(make_video(tmp_path / "long.mp4", seconds=10)))

    frames = source.frames()
    next(frames)
    frames.close()

    assert spawned
    assert all(proc.poll() is not None for proc in spawned)


def test_missing_file_raises(tmp_path):
    with pytest.raises(sources.SourceError):
        sources.open_source(str(tmp_path / "nope.png"))


@needs_ffmpeg
def test_non_media_file_raises(tmp_path):
    path = tmp_path / "fake.mp4"
    path.write_text("not a video")

    with pytest.raises(sources.SourceError):
        sources.open_source(str(path))
