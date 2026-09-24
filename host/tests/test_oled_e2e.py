import socket
import threading

import pytest
from PIL import Image

import convert
import oled
import protocol
import sources
from test_sources import make_gif


class FakeDevice:
    def __init__(self, close_after=None):
        self.close_after = close_after
        self.messages = []
        self.server = socket.create_server(("127.0.0.1", 0))
        self.port = self.server.getsockname()[1]
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

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
        self.server.close()

    def wait(self):
        self.thread.join(5)
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
    device = FakeDevice()

    code = run_main([str(path), "--host", "127.0.0.1", "--port", str(device.port)])

    expected = convert.to_frame(Image.open(path), "fit", "fs", False)
    assert code == 0
    assert device.wait() == [(protocol.MSG_FRAME, expected)]


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


def test_missing_file_fails_before_connecting(tmp_path, capsys, monkeypatch):
    def fail_connect(*args, **kwargs):
        pytest.fail("connected despite missing file")

    monkeypatch.setattr(oled.sender, "connect", fail_connect)

    code = run_main([str(tmp_path / "nope.png"), "--host", "127.0.0.1"])

    assert code == 1
    assert "file not found" in capsys.readouterr().err
