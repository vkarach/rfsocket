import re
import socket
import struct
import threading
import time

import pytest
from PIL import Image

import clip
import convert
import oled
import protocol
import sources
from test_sources import make_gif


class FakeDevice:
    """First connection is the frame stream; later connections speak STORE."""

    def __init__(self, close_after=None, close_delay=0.0, store_reply=protocol.STORE_ACCEPT,
                 cut_payload=False):
        self.close_after = close_after
        self.close_delay = close_delay
        self.store_reply = store_reply
        self.cut_payload = cut_payload
        self.messages = []
        self.stores = []
        self.server = socket.create_server(("127.0.0.1", 0))
        self.port = self.server.getsockname()[1]
        threading.Thread(target=self._run, daemon=True).start()

    def _recv_exact(self, conn, size):
        data = b""
        while len(data) < size:
            chunk = conn.recv(size - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def _run(self):
        conn, _ = self.server.accept()
        with conn:
            while self.close_after is None or len(self.messages) < self.close_after:
                header = self._recv_exact(conn, 1)
                if header is None:
                    break
                self.messages.append((header[0], self._recv_exact(conn, protocol.FRAME_SIZE)))
            time.sleep(self.close_delay)
        while True:
            try:
                conn, _ = self.server.accept()
            except OSError:
                return
            with conn:
                self._serve_store(conn)

    def _serve_store(self, conn):
        kind, clip_id, keep, name_length = struct.unpack(">B12sBB", self._recv_exact(conn, 15))
        assert kind == protocol.MSG_STORE
        name = self._recv_exact(conn, name_length).decode()
        frames, size = struct.unpack(">II", self._recv_exact(conn, 8))
        conn.sendall(bytes([self.store_reply]))
        if self.store_reply != protocol.STORE_ACCEPT:
            return
        if self.cut_payload:
            self._recv_exact(conn, 1)
            return
        payload = self._recv_exact(conn, size)
        self.stores.append((clip_id.decode(), bool(keep), name, frames, payload))
        conn.sendall(bytes([protocol.STORE_DONE]))

    def wait(self):
        return self.messages


def run_main(argv):
    result = {}
    thread = threading.Thread(target=lambda: result.setdefault("code", oled.main(argv)), daemon=True)
    thread.start()
    thread.join(5)
    assert not thread.is_alive(), "oled.main hung"
    return result["code"]


def test_png_sends_one_converted_frame(tmp_path):
    path = tmp_path / "pic.png"
    Image.new("RGB", (80, 40), (255, 255, 255)).save(path)
    device = FakeDevice(close_after=1)

    code = run_main([str(path), "--host", "127.0.0.1", "--port", str(device.port)])

    expected = convert.to_frame(Image.open(path), "fit", "fs", False)
    assert code == 0
    assert device.wait() == [(protocol.MSG_FRAME, expected)]


def test_png_holds_connection_until_device_closes(tmp_path, capsys):
    path = tmp_path / "pic.png"
    Image.new("L", (8, 8), 255).save(path)
    device = FakeDevice(close_after=1, close_delay=0.6)

    started = time.monotonic()
    code = run_main([str(path), "--host", "127.0.0.1", "--port", str(device.port)])

    assert code == 0
    assert time.monotonic() - started >= 0.5
    assert "sent 1, dropped 0" in capsys.readouterr().out


def test_loop_interrupted_still_prints_stats(tmp_path, capsys, monkeypatch):
    path = make_gif(tmp_path / "anim.gif", [20, 20, 20])
    device = FakeDevice()
    real_to_frame = convert.to_frame
    calls = []

    def interrupt_after_five(*args):
        calls.append(None)
        if len(calls) > 5:
            raise KeyboardInterrupt
        return real_to_frame(*args)

    monkeypatch.setattr(oled.convert, "to_frame", interrupt_after_five)

    code = run_main([str(path), "--host", "127.0.0.1", "--port", str(device.port), "--loop"])

    match = re.search(r"sent (\d+), dropped (\d+)", capsys.readouterr().out)
    assert code == 0
    assert match and int(match.group(1)) >= 1


def test_gif_sends_frames_in_order(tmp_path):
    path = make_gif(tmp_path / "anim.gif", [20, 20, 20])
    device = FakeDevice()

    code = run_main([str(path), "--host", "127.0.0.1", "--port", str(device.port), "--dither", "none"])

    expected = [(protocol.MSG_FRAME, convert.to_frame(image, "fit", "none", False))
                for image, _ in sources.open_source(str(path)).frames()]
    assert code == 0
    assert len(set(frame for _, frame in expected)) > 1
    assert device.wait() == expected


def test_device_disconnect_reports_connection_lost(tmp_path, capsys):
    path = make_gif(tmp_path / "long.gif", [20] * 100)
    device = FakeDevice(close_after=1)

    code = run_main([str(path), "--host", "127.0.0.1", "--port", str(device.port)])

    assert code == 1
    assert "connection lost" in capsys.readouterr().err


def test_unreachable_device_exits_with_error(tmp_path, capsys):
    path = tmp_path / "pic.png"
    Image.new("L", (8, 8)).save(path)
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()

    code = run_main([str(path), "--host", "127.0.0.1", "--port", str(port)])

    assert code == 1
    assert "cannot connect" in capsys.readouterr().err


REAL_TO_FRAME = convert.to_frame


def expected_clip(path, dither, durations):
    builder = clip.ClipBuilder(str(path))
    images = [image for image, _ in sources.open_source(str(path)).frames()]
    for image, duration in zip(images, durations):
        builder.add(REAL_TO_FRAME(image, "fit", dither, False), duration)
    return builder.finish()


def interrupt_after(monkeypatch, calls_allowed):
    calls = []

    def to_frame(*args):
        calls.append(None)
        if len(calls) > calls_allowed:
            raise KeyboardInterrupt
        return REAL_TO_FRAME(*args)

    monkeypatch.setattr(oled.convert, "to_frame", to_frame)


def test_png_is_uploaded_to_history_after_stream(tmp_path, capsys):
    path = tmp_path / "pic.png"
    Image.new("RGB", (80, 40), (255, 255, 255)).save(path)
    device = FakeDevice(close_after=1)

    code = run_main([str(path), "--host", "127.0.0.1", "--port", str(device.port)])

    built = expected_clip(path, "fs", [0])
    assert code == 0
    assert device.stores == [(built.id, False, "pic.png", 1, built.data)]
    assert "saved %s" % built.id in capsys.readouterr().out


def test_looped_gif_uploads_exactly_one_pass(tmp_path, monkeypatch):
    path = make_gif(tmp_path / "anim.gif", [20, 20, 20])
    device = FakeDevice()
    interrupt_after(monkeypatch, 7)

    code = run_main([str(path), "--host", "127.0.0.1", "--port", str(device.port), "--loop"])

    built = expected_clip(path, "bayer", [0.02, 0.02, 0.02])
    assert code == 0
    assert [(s[0], s[3]) for s in device.stores] == [(built.id, 3)]


def test_incomplete_first_pass_is_not_uploaded(tmp_path, monkeypatch, capsys):
    path = make_gif(tmp_path / "anim.gif", [20, 20, 20])
    device = FakeDevice()
    interrupt_after(monkeypatch, 2)

    code = run_main([str(path), "--host", "127.0.0.1", "--port", str(device.port)])

    assert code == 0
    assert device.stores == []
    assert "not saved" in capsys.readouterr().out


def test_keep_flag_is_sent(tmp_path):
    path = make_gif(tmp_path / "anim.gif", [20, 20])
    device = FakeDevice()

    run_main([str(path), "--host", "127.0.0.1", "--port", str(device.port), "--keep"])

    assert [s[1] for s in device.stores] == [True]


@pytest.mark.parametrize("reply, text", [
    (protocol.STORE_EXISTS, "already saved"),
    (protocol.STORE_TOO_LARGE, "too large for history"),
    (protocol.STORE_NO_SPACE, "no space (starred clips fill the budget)"),
])
def test_store_replies_are_reported(tmp_path, capsys, reply, text):
    path = make_gif(tmp_path / "anim.gif", [20, 20])
    device = FakeDevice(store_reply=reply)

    code = run_main([str(path), "--host", "127.0.0.1", "--port", str(device.port)])

    assert code == 0
    assert text in capsys.readouterr().out


def test_device_closing_mid_upload_is_an_error(tmp_path, capsys):
    path = make_gif(tmp_path / "anim.gif", [20, 20])
    device = FakeDevice(cut_payload=True)

    code = run_main([str(path), "--host", "127.0.0.1", "--port", str(device.port)])

    assert code == 1
    assert "upload failed" in capsys.readouterr().err


def test_missing_file_fails_before_connecting(tmp_path, capsys, monkeypatch):
    def fail_connect(*args, **kwargs):
        pytest.fail("connected despite missing file")

    monkeypatch.setattr(oled.sender, "connect", fail_connect)

    code = run_main([str(tmp_path / "nope.png"), "--host", "127.0.0.1"])

    assert code == 1
    assert "file not found" in capsys.readouterr().err
