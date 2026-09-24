WIDTH = 128
HEIGHT = 64
FRAME_SIZE = WIDTH * HEIGHT // 8

MSG_FRAME = 0x01


def frame_message(frame):
    if len(frame) != FRAME_SIZE:
        raise ValueError("frame must be %d bytes, got %d" % (FRAME_SIZE, len(frame)))
    return bytes((MSG_FRAME,)) + bytes(frame)
