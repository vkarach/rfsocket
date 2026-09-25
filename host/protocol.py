WIDTH = 128
HEIGHT = 64
FRAME_SIZE = WIDTH * HEIGHT // 8

MSG_FRAME = 0x01
MSG_STORE = 0x02

STORE_ACCEPT = 0
STORE_EXISTS = 1
STORE_TOO_LARGE = 2
STORE_NO_SPACE = 3
STORE_DONE = 4
STORE_FAILED = 5


def frame_message(frame):
    if len(frame) != FRAME_SIZE:
        raise ValueError("frame must be %d bytes, got %d" % (FRAME_SIZE, len(frame)))
    return bytes((MSG_FRAME,)) + bytes(frame)
