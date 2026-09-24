import socket

import pytest

import protocol
import sender


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += max(seconds, 0)


class StubSocket:
    def __init__(self, clock, send_cost=0.0, error=None):
        self.clock = clock
        self.send_cost = send_cost
        self.error = error
        self.sent = []

    def sendall(self, data):
        if self.error:
            raise self.error
        self.sent.append((self.clock.now, data))
        self.clock.now += self.send_cost


def numbered_frames(count, duration):
    return [(bytes([i]) * protocol.FRAME_SIZE, duration) for i in range(count)]


def play(sock, frames, clock):
    return sender.play(sock, frames, clock=clock, sleep=clock.sleep)


def test_fast_device_gets_every_frame_on_schedule():
    clock = FakeClock()
    sock = StubSocket(clock)

    stats = play(sock, numbered_frames(5, 0.1), clock)

    assert (stats.sent, stats.dropped) == (5, 0)
    assert [t for t, _ in sock.sent] == pytest.approx([0.0, 0.1, 0.2, 0.3, 0.4])
    assert [data for _, data in sock.sent] == [protocol.frame_message(f) for f, _ in numbered_frames(5, 0.1)]


def test_slow_device_drops_frames_but_keeps_wall_clock_and_last_frame():
    clock = FakeClock()
    sock = StubSocket(clock, send_cost=0.25)
    frames = numbered_frames(10, 0.1)

    stats = play(sock, frames, clock)

    assert stats.dropped > 0
    assert stats.sent + stats.dropped == 10
    assert sock.sent[-1][1] == protocol.frame_message(frames[-1][0])
    assert clock.now <= 1.0 + 0.1 + 0.25


def test_single_still_frame_is_sent_once():
    clock = FakeClock()
    sock = StubSocket(clock)

    stats = play(sock, numbered_frames(1, 0), clock)

    assert (stats.sent, stats.dropped) == (1, 0)


def test_send_failure_becomes_connection_lost():
    clock = FakeClock()
    sock = StubSocket(clock, error=ConnectionResetError())

    with pytest.raises(sender.SenderError, match="connection lost"):
        play(sock, numbered_frames(3, 0.1), clock)


def test_connect_to_closed_port_raises_with_address():
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()

    with pytest.raises(sender.SenderError, match="127.0.0.1:%d" % port):
        sender.connect("127.0.0.1", port, timeout=1.0)
